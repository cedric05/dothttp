import concurrent.futures
import json
import logging
import sys
from json import JSONDecodeError
from typing import Dict

from . import Command, BaseHandler
from .commands import RunHttpFileHandler, FormatHttpFileHandler, GetNameReferencesHandler, ImportPostmanCollection, \
    ContentExecuteHandler, ParseHttpData, ContentNameReferencesHandler

logger = logging.getLogger('handler')

handlers: Dict[str, BaseHandler] = {handler.get_method(): handler for handler in
                                    (FormatHttpFileHandler(), RunHttpFileHandler(), GetNameReferencesHandler(),
                                     ImportPostmanCollection(),
                                     ContentExecuteHandler(),
                                     ParseHttpData(),
                                     ContentNameReferencesHandler()
                                     )}


def run(command: Command) -> Dict:
    try:
        instance: BaseHandler = handlers.get(command.method)
        result = instance.run(command)
        return {"id": result.id, "result": result.result}
    except Exception as e:
        logger.error("unknown error happened", exc_info=True)
        return {"id": command.id, "result": {"error": True, "error_message": str(e.args)}}


class Base:

    def run_forever(self):
        raise NotImplementedError

    def get_command(self, **kwargs):
        return Command(**kwargs)


class HttpServer(Base):
    def __init__(self, port=5000):
        from flask import Flask
        app = Flask("dothttp-server")
        self.app = app
        self.port = port

    def run_forever(self):
        for handler in handlers.keys():
            api = self.get_handler(handler)
            api = self.app.route(handler, methods=["POST"])(api)
        self.app.run("localhost", self.port)

    def get_handler(self, handler):
        def flask_api_handler():
            from flask import request
            try:
                id = int(request.args['id'])
                command = {'method': handler, 'params': json.loads(request.data), 'id': id}
                command = super(HttpServer, self).get_command(**command)
                result = run(command)
                return result
            except JSONDecodeError:
                logger.error(f"jsondecode error happened message: {request.data} args: {request.args}")
                return {}

        flask_api_handler.__name__ = handler
        return flask_api_handler


class CmdServer(Base):
    def __init__(self):
        self.pool = concurrent.futures.ThreadPoolExecutor()

    def run_forever(self):
        for line in sys.stdin:
            try:
                logger.debug(f"got request {line}")
                command = self.get_command(line)
                self.pool.submit(self.run_respond, command)
            except JSONDecodeError:
                logger.info(f"input line `{line.strip()}` is not json decodable")
                self.write_result({"id": 0, "result": {"error": True, "error_message": "not json decodable"}})
            except Exception as e:
                logger.info(f"unknown exception `{e}` happened ", exc_info=True)
                self.write_result({"id": 0, "result": {"error": True, "error_message": "not json decodable"}})

    def run_respond(self, command):
        result = run(command)
        self.write_result(result)

    def write_result(self, result):
        sys.stdout.write(json.dumps(result) + "\n")
        sys.stdout.flush()

    def get_command(self, line):
        output = json.loads(line)
        return super().get_command(**output)
