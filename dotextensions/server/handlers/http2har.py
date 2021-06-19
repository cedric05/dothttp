import os

from . import logger
from .basic_handlers import RunHttpFileHandler, ContentExecuteHandler
from ..models import Command, Result, BaseHandler


class Http2Har(BaseHandler):
    name = "/file/parse"

    def get_method(self):
        return Http2Har.name

    def run(self, command: Command) -> Result:
        # certificate is not supported by har format
        # visit http://www.softwareishard.com/blog/har-12-spec/#request
        # for more information
        params = command.params
        filename = params.get("file")
        content = params.get('content')
        result = Result(id=command.id)
        if not (filename and os.path.exists(filename) and os.path.isfile(filename)) and not content:
            result.result = {"error_message": "filename or content is mandatory", "error": True}
            return result
        try:
            if filename:
                executor = RunHttpFileHandler()
            else:
                executor = ContentExecuteHandler()
            config = executor.get_config(command)
            request_compiler_obj = executor.get_request_comp(config)
            request_compiler_obj.load()
            request_compiler_obj.load_def()
            result.result = {"target": {config.target: request_compiler_obj.httpdef.get_har()}}
            return result
        except Exception as e:
            logger.error("unknown error happened", exc_info=True)
            result.result = {"error_message": str(e), "error": True}
            return result
