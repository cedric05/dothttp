from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict


@dataclass
class Command:
    method: str
    params: Dict  # query params
    id: int
    initiated: datetime = field(default_factory=lambda: datetime.now())


@dataclass
class Result:
    id: int = None
    result: Dict = field(default_factory=lambda: {})

    @staticmethod
    def get_result(command: Command, result: {}):
        return Result(id=command.id, result=result)

    @staticmethod
    def to_error(command: Command, error_message: str):
        return Result(id=command.id, result={"error": True, "error_message": error_message})


class BaseHandler:

    def get_method(self):
        raise NotImplementedError

    def run(self, command: Command) -> Result:
        raise NotImplementedError


class DothttpTypes(Enum):
    NAME = "name"
    EXTRA_ARGS = "extra_args"
    URL = "url"
    BASIC_AUTH = "basic_auth"
    DIGEST_AUTH = "digest_auth"
    CERTIFICATE = "certificate"
    HEADER = "header"
    URL_PARAMS = "urlparams"
    PAYLOAD_DATA = "payload_data"
    PAYLOAD_ENCODED = "payload_urlencoded"
    PAYLOAD_FILE = "payload_file_input"
    PAYLOAD_JSON = "payload_json"
    PAYLOAD_MULTIPART = "payload_multipart"
    OUTPUT = "output"
    SCRIPT = "script"
    COMMENT = "comment"
