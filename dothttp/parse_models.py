from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Allhttp:
    pass


@dataclass
class NameWrap:
    name: str


@dataclass
class UrlWrap:
    method: str
    url: str


@dataclass
class BasicAuth:
    username: str
    password: str


@dataclass
class Query:
    key: str
    value: str


@dataclass
class Header:
    key: str
    value: str


@dataclass
class Line:
    header: Optional[Header]
    query: Optional[Query]


@dataclass
class MultiPartFile:
    name: str
    path: str
    type: Optional[str] = None


@dataclass
class FilesWrap:
    files: List[MultiPartFile]


@dataclass
class Payload:
    data: Optional[str]
    datajson: Optional
    file: Optional[str]
    json: Optional
    fileswrap: Optional[FilesWrap]
    type: Optional[str]


@dataclass
class ToFile:
    output: str


@dataclass
class Http:
    namewrap: Optional[NameWrap]
    urlwrap: UrlWrap
    basic_auth_wrap: Optional[BasicAuth]
    lines: Optional[List[Line]]
    payload: Optional[Payload]
    output: Optional[ToFile]


@dataclass
class Allhttp:
    allhttps: List[Http]
