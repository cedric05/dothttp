from dothttp import RequestCompiler, Config, DotHttpException, dothttp_model
from . import Command, Result, BaseHandler


class RunHttpFileHandler(BaseHandler):
    name = "/file/execute"

    def get_method(self):
        return RunHttpFileHandler.name

    def run(self, command: Command) -> Result:
        filename = command.params.get("file")
        envs = command.params.get("env", [])
        target = command.params.get("target", '1')
        nocookie = command.params.get("nocookie", False)
        curl = command.params.get("curl", False)
        props = command.params.get('properties', {})
        properties = [f"{i}={j}" for i, j in props.items()]
        try:
            request = RequestCompiler(Config(file=filename,
                                             env=envs,
                                             properties=properties,
                                             curl=curl,
                                             property_file=None,
                                             debug=True,
                                             no_cookie=nocookie,
                                             format=False,
                                             info=False,
                                             target=target
                                             ))
            resp = request.get_response()
            result = Result(id=command.id,
                            result={
                                "headers":
                                    {key: value for key, value in resp.headers.items()},
                                "body": resp.text,
                                "status": resp.status_code,
                            })
        except DotHttpException as ex:
            result = Result(id=command.id,
                            result={
                                "error_message": ex.message, "error": True})
        return result


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
            with open(filename) as f:
                http_data = f.read()
                model = dothttp_model.model_from_str(http_data)
                all_names = []
                for index, http in enumerate(model.allhttps):
                    if http.namewrap:
                        name = http.namewrap.name if http.namewrap else str(index)
                        start = http.namewrap._tx_position
                        end = http.namewrap._tx_position_end
                    else:
                        start = http.urlwrap._tx_position
                        end = http.urlwrap._tx_position_end
                        name = str(index)
                    name = {
                        'name': name,
                        'start': start,
                        'end': end
                    }
                    all_names.append(name)
                result = Result(id=command.id, result={"names": all_names})
        except DotHttpException as ex:
            result = Result(id=command.id,
                            result={
                                "error_message": ex.message, "error": True})
        except Exception as e:
            result = Result(id=command.id,
                            result={
                                "error_message": str(e), "error": True})
        return result
