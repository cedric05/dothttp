from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict


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
