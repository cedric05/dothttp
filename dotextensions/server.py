import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from json import JSONDecodeError
from typing import Dict

from dothttp import RequestCompiler, Config, DotHttpException
from dothttp.log_utils import setup_logging as root_logging_setup

logger = logging.getLogger('handler')


@dataclass
class Command:
    method: str
    params: Dict  # query params
    id: int
    initiated: datetime = field(default_factory=lambda: datetime.now())


@dataclass
class Result:
    id: int
    result: Dict = field(default_factory=lambda: {})


class BaseHandler:

    def get_method(self):
        raise NotImplementedError

    def run(self, command: Command) -> Result:
        raise NotImplementedError


class RunHttpFileHandler(BaseHandler):
    name = "/file/execute"

    def get_method(self):
        return RunHttpFileHandler.name

    def run(self, command: Command) -> Result:
        filename = command.params.get("file")
        envs = command.params.get("env", [])
        nocookie = command.params.get("nocookie", False)
        props = command.params.get('properties', {})
        properties = [f"{i}={j}" for i, j in props.items()]
        try:
            request = RequestCompiler(Config(file=filename,
                                             env=envs,
                                             properties=properties,
                                             curl=False,
                                             property_file=None,
                                             debug=True,
                                             no_cookie=nocookie,
                                             format=False,
                                             info=False
                                             ))
            resp = request.get_response()
            result = Result(id=command.id,
                            result={
                                "headers":
                                    {key: value for key, value in resp.headers.items()},
                                "body": resp.text})
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


handlers: Dict[str, BaseHandler] = {handler.get_method(): handler for handler in
                                    (FormatHttpFileHandler(), RunHttpFileHandler())}


def run(command: Command) -> Dict:
    instance: BaseHandler = handlers.get(command.method)
    result = instance.run(command)
    return {"id": result.id, "result": result.result}


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
        from flask import request
        def flask_api_handler():
            try:
                id = int(request.args['id'])
                command = {'method': handler, 'params': json.loads(request.data), 'id': id}
                command = super(HttpServer, self).get_command(**command)
                result = run(command)
                return result
            except JSONDecodeError:
                return {}

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
        return super().get_command(**output)


def setup_logging(level):
    root_logging_setup(level)
    logging.getLogger("cmd-server").setLevel(level)
    logging.getLogger('handler').setLevel(level)
    logging.root.setLevel(level)


def main():
    setup_logging(logging.DEBUG)
    if len(sys.argv) == 2:
        type_of_server = sys.argv[1]
    else:
        type_of_server = "cmd"
    if type_of_server == "cmd":
        CmdServer().run_forever()
    elif type_of_server == "http":
        port = 5000
        if len(sys.argv) == 3:
            try:
                port = int(sys.argv[3])
            except ValueError:
                pass
        HttpServer(port).run_forever()
    sys.exit(1)


if __name__ == "__main__":
    main()
