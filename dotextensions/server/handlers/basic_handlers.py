import mimetypes

from requests import RequestException

from dothttp import DotHttpException, Config, HttpDef, Allhttp
from dothttp.request_base import CurlCompiler, RequestCompiler, HttpFileFormatter, dothttp_model
from . import logger
from ..models import Command, Result, BaseHandler


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
        filename = command.params.get("file")
        envs = command.params.get("env", [])
        target = command.params.get("target", '1')
        nocookie = command.params.get("nocookie", False)
        curl = command.params.get("curl", False)
        props = command.params.get('properties', {})
        properties = [f"{i}={j}" for i, j in props.items()]
        content = command.params.get("content")
        if content:
            try:
                content = "\n".join(content.splitlines())
            except:
                content = None
        config = Config(file=filename, env=envs, properties=properties, curl=curl, property_file=None, debug=True,
                        no_cookie=nocookie, format=False, info=False, target=target, content=content)
        return config

    def get_request_result(self, command, comp: RequestCompiler):
        resp = comp.get_response()
        script_result = comp.execute_script(resp).as_json()
        response_data = {
            "response": {
                "headers":
                    {key: value for key, value in resp.headers.items()},
                "body": resp.text,  # for binary out, it will fail, check for alternatives
                "status": resp.status_code,
                "method": resp.request.method,
                "url": resp.url},
            "script_result": script_result,
        }
        # will be used for response
        data = {}
        data.update(response_data['response'])  # deprecated
        data.update(response_data)
        data.update({"http": self.get_http_from_req(comp.httpdef)})
        result = Result(id=command.id,
                        result=data)
        return result

    def get_request_comp(self, config):
        return RequestCompiler(config)

    @staticmethod
    def get_http_from_req(request: HttpDef):
        http_def = Allhttp([request.get_http_from_req()])
        return HttpFileFormatter.format(http_def)


class ContentBase:
    def __init__(self, config: Config):
        super().__init__(config)

    def load_content(self):
        self.original_content = self.content = self.args.content


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
