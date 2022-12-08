import mimetypes
from typing import List

from requests import RequestException

from dothttp import DotHttpException, Config, HttpDef, Allhttp, BaseModelProcessor, UndefinedHttpToExtend, js3py
from dothttp.request_base import CurlCompiler, RequestCompiler, HttpFileFormatter, dothttp_model
from dothttp.__version__ import __version__
from dothttp.parse_models import ScriptType
from . import logger
from ..models import Command, Result, BaseHandler


class ContextConfig(Config):
    contexts: List[str] = None


class VersionHandler(BaseHandler):
    name = "/version"

    def get_method(self):
        return VersionHandler.name

    def run(self, command: Command) -> Result:
        return Result(id=command.id,
                            result={
                                "version": __version__})

class RunHttpFileHandler(BaseHandler):
    name = "/file/execute"

    def get_method(self):
        return RunHttpFileHandler.name

    def run(self, command: Command) -> Result:
        config = self.get_config(command)
        try:
            if config.curl:
                req = self.get_curl_comp(config)
                result = req.get_curl_output()
                result = Result(id=command.id, result={
                    "body": result,
                    "headers": {
                        "Content-Type": mimetypes.types_map['.sh'],
                    }
                })
            else:
                comp = self.get_request_comp(config)
                result = self.get_request_result(command, comp)
        except DotHttpException as exc:
            logger.error(f'dothttp exception happened {exc}', exc_info=True)
            result = Result(id=command.id,
                            result={
                                "error_message": exc.message, "error": True})
        except RequestException as exc:
            logger.error(f'exception from requests {exc}', exc_info=True)
            result = Result(id=command.id,
                            result={
                                "error_message": str(exc), "error": True})
        except Exception as exc:
            logger.error(f'unknown error happened {exc}', exc_info=True)
            result = Result(id=command.id,
                            result={
                                "error_message": str(exc), "error": True})

        return result

    def get_curl_comp(self, config):
        return CurlCompiler(config)

    def get_config(self, command):
        params = command.params
        filename = params.get("file")
        envs = params.get("env", [])
        target = params.get("target", '1')
        nocookie = params.get("nocookie", False)
        curl = params.get("curl", False)
        properties = [f"{i}={j}" for i, j in params.get('properties', {}).items()]
        content = params.get("content", None)
        contexts = params.get("contexts")
        if contexts is None:
            contexts = []
        if content:
            try:
                content = "\n".join(content.splitlines())
            except:
                content = None
        config = ContextConfig(file=filename, env=envs, properties=properties, curl=curl, property_file=None,
                               debug=True,
                               no_cookie=nocookie, format=False, info=False, target=target, content=content)
        config.contexts = contexts
        return config

    def get_request_result(self, command, comp: RequestCompiler):
        comp.load_def()
        execution_cls = js3py.ScriptExecutionJs  if comp.httpdef.test_script_lang == ScriptType.JAVA_SCRIPT  else js3py.ScriptExecutionPython
        script_execution = execution_cls(comp.httpdef, comp.property_util)
        script_execution.pre_request_script()
        resp = comp.get_response()
        if output := comp.httpdef.output:
            # body = f"Output stored in {output}"
            try:
                comp.write_to_output(resp)
            except Exception as e:
                output = f"Not!. unhandled error happened : {e}"
                logger.warning("unable to write because", exc_info=True)
        script_result = script_execution.execute_test_script(resp).as_json()
        body = resp.text
        response_data = {
            "response": {
                "body": body,  # for binary out, it will fail, check for alternatives
                "output_file": output or "",
                **self._get_resp_data(resp)
            },
            "script_result": script_result,
        }
        if resp.history:
            response_data["history"] = [self._get_resp_data(hist_item) for hist_item in resp.history]
        # will be used for response
        data = {}
        data.update(response_data['response'])  # deprecated
        data.update(response_data)
        if not comp.args.no_cookie and 'cookie' in resp.request.headers:
            # redirects can add cookies
            comp.httpdef.headers['cookie'] = resp.request.headers['cookie']
        try:
            data.update({"http": self.get_http_from_req(comp.httpdef)})
        except Exception as e:
            logger.error("ran into error regenerating http def from parsed object")
            data.update({"http": f"ran into error \n Exception: `{e}` message:{e.args}"})
        result = Result(id=command.id,
                        result=data)
        return result

    def _get_resp_data(self, resp):
        return {
            "headers": {key: value for key, value in resp.headers.items()},
            "status": resp.status_code,
            "method": resp.request.method,
            "url": resp.url
        }

    def get_request_comp(self, config):
        return RequestCompiler(config)

    @staticmethod
    def get_http_from_req(request: HttpDef):
        http_def = Allhttp([request.get_http_from_req()])
        return HttpFileFormatter.format(http_def)


CONTEXT_SEP = """
# include contexts from context, to resolve properties
"""


class ContentBase(BaseModelProcessor):
    def __init__(self, config: ContextConfig):
        super().__init__(config)
        self.args = config

    def load_content(self):
        # joining contexts to content is not correct approach
        # as any error in one of context could bring down main usecase
        self.original_content = self.content = self.args.content

    def load_model(self):
        # reqcomp will try to resolve properties right after model is generated
        super(ContentBase, self).load_model()
        ##
        ## context has varibles defined
        ## for resolving purpose, including them into content
        self.content = self.content + CONTEXT_SEP + CONTEXT_SEP.join(
            self.args.contexts)

    def select_target(self):
        try:
            # first try to resolve target from current context
            super().select_target()
        except UndefinedHttpToExtend as ex:
            # if it weren't able to figure out context, try to resolve from contexts
            for context in self.args.contexts:
                try:
                    # if model is generated, try to figure out target
                    model: Allhttp = dothttp_model.model_from_str(context)
                    # by including targets in to model
                    self.model.allhttps = self.model.allhttps + model.allhttps
                    self.content += context + "\n\n" + context
                    return super(ContentBase, self).select_target()
                except Exception as e:
                    # contexts, can not always be correct syntax
                    # in such scenarios, don't complain, try to resolve with next contexts
                    logger.info("ignoring exception, context is not looking good")
            raise ex


class ContentRequestCompiler(ContentBase, RequestCompiler):
    pass


class ContentCurlCompiler(ContentBase, CurlCompiler):
    pass


class ContentExecuteHandler(RunHttpFileHandler):
    name = "/content/execute"

    def get_config(self, command):
        config = super().get_config(command)
        # config.file = command.params.get('content')
        return config

    def get_method(self):
        return ContentExecuteHandler.name

    def get_request_comp(self, config):
        return ContentRequestCompiler(config)

    def get_curl_comp(self, config):
        return ContentCurlCompiler(config)


class FormatHttpFileHandler(BaseHandler):
    method = "/file/format"

    def get_method(self):
        return FormatHttpFileHandler.method

    def run(self, command: Command) -> Result:
        result = Result(id=command.id, result=command.params)
        return result


class GetNameReferencesHandler(BaseHandler):
    name = "/file/names"

    def get_method(self):
        return GetNameReferencesHandler.name

    def run(self, command: Command) -> Result:
        filename = command.params.get("file")
        try:
            result = self.execute(command, filename)
        except DotHttpException as ex:
            result = Result(id=command.id,
                            result={
                                "error_message": ex.message, "error": True})
        except Exception as e:
            result = Result(id=command.id,
                            result={
                                "error_message": str(e), "error": True})
        return result

    def execute(self, command: Command, filename):
        with open(filename) as f:
            http_data = f.read()
            all_names, all_urls = self.parse_n_get(http_data)
            result = Result(id=command.id, result={"names": all_names, "urls": all_urls})
        return result

    def parse_n_get(self, http_data):
        model = dothttp_model.model_from_str(http_data)
        all_names = []
        all_urls = []
        for index, http in enumerate(model.allhttps):
            if http.namewrap:
                name = http.namewrap.name if http.namewrap else str(index)
                start = http.namewrap._tx_position
                end = http._tx_position_end
            else:
                start = http.urlwrap._tx_position
                end = http._tx_position_end
                name = str(index + 1)
            name = {
                'name': name,
                'method': http.urlwrap.method,
                'start': start,
                'end': end
            }
            url = {
                'url': http.urlwrap.url,
                'method': http.urlwrap.method or 'GET',
                'start': http.urlwrap._tx_position,
                'end': http.urlwrap._tx_position_end,
            }
            all_names.append(name)
            all_urls.append(url)
        return all_names, all_urls


class ContentNameReferencesHandler(GetNameReferencesHandler):
    name = "/content/names"

    def get_method(self):
        return ContentNameReferencesHandler.name

    def execute(self, command, filename):
        http_data = command.params.get("content", "")
        all_names, all_urls = self.parse_n_get(http_data)
        result = Result(id=command.id, result={"names": all_names, "urls": all_urls})
        return result
