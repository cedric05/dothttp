import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

from dothttp import RequestCompiler, Config

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
