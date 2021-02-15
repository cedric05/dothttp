import json
import logging
import sys
from json import JSONDecodeError
from typing import Dict

from flask import Flask
from flask import request

from . import handlers, Command, BaseHandler

logger = logging.getLogger('handler')


def run(command: Command) -> Dict:
    instance: BaseHandler = handlers.get(command.method)
    result = instance.run(command)
    return {"id": result.id, "result": result.result}


class Base:

    def run_forever(self):
        raise NotImplementedError


class HttpServer(Base):
    def __init__(self, port=5000):
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
            data = json.loads(request.data)
            data['method'] = handler
            command = Command(**data)
            result = run(command)
            return result

        flask_api_handler.__name__ = handler
        return flask_api_handler


class CmdServer(Base):

    def run_forever(self):
        for line in sys.stdin:
            try:
                logger.debug(f"got request {line}")
                command = self.get_command(line)
                result = run(command)
                sys.stdout.write(json.dumps(result) + "\n")
            except JSONDecodeError:
                logger.info(f"input line `{line}` is not json decodable")
            except Exception as e:
                logger.info(f"unknown exception `{e}` happened ")

    def get_command(self, line):
        output = json.loads(line)
        return Command(**output)
