import concurrent.futures
import json
import logging
import sys
from json import JSONDecodeError
from typing import Dict
import asyncio
import typing

from dothttp.__version__ import __version__ as version
from .handlers.basic_handlers import RunHttpFileHandler, ContentExecuteHandler, FormatHttpFileHandler, \
    GetNameReferencesHandler, ContentNameReferencesHandler, VersionHandler
from .handlers.gohandler import TypeFromPos
from .handlers.har2httphandler import Har2HttpHandler
from .handlers.http2har import Http2Har
from .handlers.http2postman import Http2Postman
from .handlers.postman2http import ImportPostmanCollection
from .models import Command, BaseHandler

logger = logging.getLogger('handler')

handlers: Dict[str, BaseHandler] = {handler.get_method(): handler for handler in
                                    (FormatHttpFileHandler(), RunHttpFileHandler(), GetNameReferencesHandler(),
                                     ImportPostmanCollection(),
                                     ContentExecuteHandler(),
                                     Http2Har(),
                                     ContentNameReferencesHandler(),
                                     TypeFromPos(),
                                     Har2HttpHandler(),
                                     Http2Postman(),
                                     VersionHandler(),
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
        from flask_cors import CORS
        app = Flask("dothttp-server")
        CORS(app)
        self.app = app
        self.port = port
        for handler in handlers.keys():
            self.app.route(handler, methods=["POST"])(self.get_handler(handler))

    def run_forever(self):
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
        # publish version
        self.write_result({"id": -1, "result": {"dothttp_version": version}})
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

async def async_read_stdin() -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sys.stdin.readline)

async def connect_stdin_stdout() -> typing.Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    w_transport, w_protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout)
    writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)
    return reader, writer

class AsyncCmdServer(CmdServer):

    async def run_forever(self):
        self.reader, self.writer = await connect_stdin_stdout()
        # publish version
        self.write_result({"id": -1, "result": {"dothttp_version": version}})
        while True:
            line = await self.reader.readline()
            try:
                logger.debug(f"got request {line}")
                command = self.get_command(line)
                if len(line) != 0:
                    await self.run_respond(command)
            except JSONDecodeError:
                logger.info(
                    f"input line `{line.strip()}` is not json decodable")
                self.write_result(
                    {"id": 0, "result": {"error": True, "error_message": "not json decodable"}})
            except Exception as e:
                logger.info(
                    f"unknown exception `{e}` happened ", exc_info=True)
                self.write_result(
                    {"id": 0, "result": {"error": True, "error_message": "not json decodable"}})

    async def run_respond(self, command):
        result = run(command)
        self.write_result(result)

    def write_result(self, result):
        string_result = json.dumps(result) + "\n"
        self.writer.write(string_result.encode())
