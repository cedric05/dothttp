import mimetypes
from typing import List

from requests import RequestException

from dothttp.__version__ import __version__
from dothttp.exceptions import DotHttpException
from dothttp.models.parse_models import ScriptType
from dothttp.parse import (
    BaseModelProcessor,
    Config,
    HttpDef,
    MultidefHttp,
    UndefinedHttpToExtend,
)
from dothttp.parse.request_base import (
    CurlCompiler,
    HttpFileFormatter,
    RequestCompiler,
    dothttp_model,
)
from ..models import BaseHandler, Command, Result
from . import logger


class ContextConfig(Config):
    contexts: List[str] = None


class VersionHandler(BaseHandler):
    name = "/version"

    def get_method(self):
        return VersionHandler.name

    def run(self, command: Command) -> Result:
        return Result(id=command.id, result={"version": __version__})


class RunHttpFileHandler(BaseHandler):
    name = "/file/execute"

    def get_method(self):
        return RunHttpFileHandler.name

    def run(self, command: Command) -> Result:
        try:
            result = self.execute(command)
        except DotHttpException as exc:
            logger.error(f"dothttp exception happened {exc}", exc_info=True)
            result = Result(
                id=command.id, result={"error_message": exc.message, "error": True}
            )
        except RequestException as exc:
            logger.error(f"exception from requests {exc}", exc_info=True)
            result = Result(
                id=command.id, result={"error_message": str(exc), "error": True}
            )
        except Exception as exc:
            logger.error(f"unknown error happened {exc}", exc_info=True)
            result = Result(
                id=command.id, result={"error_message": str(exc), "error": True}
            )
        return result

    def execute(self, command):
        config = self.get_config(command)
        if config.curl:
            req = self.get_curl_comp(config)
            result = req.get_curl_output()
            result = Result(
                    id=command.id,
                    result={
                        "body": result,
                        "headers": {
                            "Content-Type": mimetypes.types_map[".sh"],
                        },
                    },
                )
        else:
            comp = self.get_request_comp(config)
            result = self.get_request_result(command, comp)
        return result

    def get_curl_comp(self, config):
        return CurlCompiler(config)

    def get_config(self, command):
        params = command.params
        filename = params.get("file")
        envs = params.get("env", [])
        target = params.get("target", "1")
        nocookie = params.get("nocookie", False)
        curl = params.get("curl", False)
        properties = [f"{i}={j}" for i, j in params.get("properties", {}).items()]
        content = params.get("content", None)
        contexts = params.get("contexts")
        property_file = params.get("property-file", None)
        if contexts is None:
            contexts = []
        if content:
            try:
                content = "\n".join(content.splitlines())
            except BaseException:
                content = None
        config = ContextConfig(
            file=filename,
            env=envs,
            properties=properties,
            curl=curl,
            property_file=property_file,
            debug=True,
            no_cookie=nocookie,
            format=False,
            info=False,
            target=target,
            content=content,
        )
        config.contexts = contexts
        return config

    def get_request_result(self, command, comp: RequestCompiler):
        comp.load_def()
        resp = comp.get_response()
        if output := comp.httpdef.output:
            # body = f"Output stored in {output}"
            try:
                comp.write_to_output(resp)
            except Exception as e:
                output = f"Not!. unhandled error happened : {e}"
                logger.warning("unable to write because", exc_info=True)
        script_result = comp.script_execution.execute_test_script(resp).as_json()
        body = resp.text
        response_data = {
            "response": {
                "body": body,  # for binary out, it will fail, check for alternatives
                "output_file": output or "",
                **self._get_resp_data(resp),
            },
            "script_result": script_result,
        }
        if resp.history:
            response_data["history"] = [
                self._get_resp_data(hist_item) for hist_item in resp.history
            ]
        # will be used for response
        data = {}
        data.update(response_data["response"])  # deprecated
        data.update(response_data)
        if not comp.args.no_cookie and "cookie" in resp.request.headers:
            # redirects can add cookies
            comp.httpdef.headers["cookie"] = resp.request.headers["cookie"]
        try:
            data.update({"http": self.get_http_from_req(comp.httpdef, comp.property_util)})
        except Exception as e:
            logger.error("ran into error regenerating http def from parsed object")
            data.update(
                {"http": f"ran into error \n Exception: `{e}` message:{e.args}"}
            )
        result = Result(id=command.id, result=data)
        return result

    def _get_resp_data(self, resp):
        return {
            "headers": {key: value for key, value in resp.headers.items()},
            "status": resp.status_code,
            "method": resp.request.method,
            "url": resp.url,
        }

    def get_request_comp(self, config):
        return RequestCompiler(config)

    @staticmethod
    def get_http_from_req(request: HttpDef, property_util: "PropertyProvider"):
        http_def = MultidefHttp(import_list=[], allhttps=[request.get_http_from_req()])
        return HttpFileFormatter.format(http_def, property_util=property_util)


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
        # context has varibles defined
        # for resolving purpose, including them into content
        self.content = self.content + CONTEXT_SEP + CONTEXT_SEP.join(self.args.contexts)

    def select_target(self):
        for context in self.args.contexts:
            try:
                # if model is generated, try to figure out target
                model: MultidefHttp = dothttp_model.model_from_str(context)
                # by including targets in to model
                self.load_properties_from_var(model, self.property_util)
                self.model.allhttps = self.model.allhttps + model.allhttps
                if model.import_list and model.import_list.filename:
                    if self.model.import_list and self.model.import_list.filename:
                        self.model.import_list.filename += (
                            model.import_list.filename
                        )
                    else:
                        self.model.import_list = model.import_list
                    self.load_imports()
                self.content += context + "\n\n" + context
                
            except Exception as e:
                # contexts, can not always be correct syntax
                # in such scenarios, don't complain, try to resolve with
                # next contexts
                logger.info("ignoring exception, context is not looking good")
        return super(ContentBase, self).select_target()


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

    def run(self, command: Command) -> Result:
        """
        When handling content, if an exception is raised, the response is not in the usual format.
        Instead, it returns an error message. It is better to respond with a structured response.
        """
        try:
            return self.execute(command)
        except DotHttpException as exc:
            logger.error(f"dothttp exception happened {exc}", exc_info=True)
            error_result = exc.message
        except RequestException as exc:
            logger.error(f"exception from requests {exc}", exc_info=True)
            error_result = str(exc)
        except Exception as exc:
            logger.error(f"unknown error happened {exc}", exc_info=True)
            error_result = str(exc)
        response = {
            "body": error_result,
            "status": 0,
            "method": "REQUEST_EXECUTION_ERROR",
            "url": "REQUEST_EXECUTION_ERROR",
            "headers": {
                "Content-Type": "text/plain",
            },
            "output_file":"",
            "error": True,
            "error_message": error_result,
            "contentType": "text/plain",
        }
        result = {
            "response": response,
            "script_result": {"stdout": "", "error": "", "properties":{}, "tests":[]},
            "http": "REQUEST_EXECUTION_ERROR",
            "filenameExtension": ".txt",
        }
        result.update(response)
        return Result(id=command.id, result=result) 

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
            result = Result(
                id=command.id, result={"error_message": ex.message, "error": True}
            )
        except Exception as e:
            result = Result(
                id=command.id, result={"error_message": str(e), "error": True}
            )
        return result

    def execute(self, command: Command, filename):
        with open(filename) as f:
            http_data = f.read()
            all_names, all_urls, imported_names, imported_urls = self.parse_n_get(
                http_data, filename
            )
            result = Result(
                id=command.id,
                result={
                    "names": all_names,
                    "urls": all_urls,
                    "imports": {"names": imported_names, "urls": imported_urls},
                },
            )
        return result

    def parse_n_get(self, http_data, filename: str):
        model: MultidefHttp = dothttp_model.model_from_str(http_data)
        all_names = []
        all_urls = []
        imported_names = []
        imported_urls = []
        self.get_for_http(model.allhttps, all_names, all_urls)
        for new_model, _content in BaseModelProcessor._get_models_from_import(
            model, filename
        ):
            self.get_for_http(new_model.allhttps, imported_names, imported_urls)
        return all_names, all_urls, imported_names, imported_urls

    def get_for_http(self, allhttps, all_names, all_urls):
        for index, http in enumerate(allhttps):
            if http.namewrap:
                name = http.namewrap.name if http.namewrap else str(index)
                start = http.namewrap._tx_position
                end = http._tx_position_end
            else:
                start = http.urlwrap._tx_position
                end = http._tx_position_end
                name = str(index + 1)
            name = {
                "name": name,
                "method": http.urlwrap.method,
                "start": start,
                "end": end,
            }
            url = {
                "url": http.urlwrap.url,
                "method": http.urlwrap.method or "GET",
                "start": http.urlwrap._tx_position,
                "end": http.urlwrap._tx_position_end,
            }
            all_names.append(name)
            all_urls.append(url)


class ContentNameReferencesHandler(GetNameReferencesHandler):
    name = "/content/names"

    def get_method(self):
        return ContentNameReferencesHandler.name

    def execute(self, command, filename):
        http_data = command.params.get("content", "")
        context = command.params.get("context", [])
        all_names, all_urls, imported_names, imported_urls = self.parse_n_get(
            http_data, filename
        )
        for context_context in context:
            try:
                (
                    _all_names,
                    _all_urls,
                    _imported_names,
                    _imported_urls,
                ) = self.parse_n_get(context_context, filename)
                imported_names += _all_names + _imported_names
                imported_urls += _all_urls + _imported_urls
            except:
                pass
        result = Result(
            id=command.id,
            result={
                "names": all_names,
                "urls": all_urls,
                "imports": {"names": imported_names, "urls": imported_urls},
            },
        )
        return result
