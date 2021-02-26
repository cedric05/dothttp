from dataclasses import dataclass
from typing import List, Optional, Dict


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


class Query:
    key: str
    value: str


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
    type: Optional[str]


@dataclass
class FilesWrap:
    files: List[MultiPartFile]


@dataclass
class Payload:
    data: Optional[str]
    datajson: Optional[Dict]
    file: Optional[str]
    json: Optional
    fileswrap: FilesWrap
    type: str


@dataclass
class ToFile:
    output: str


@dataclass
class Http:
    namewrap: Optional[NameWrap]
    urlwrap: UrlWrap
    basic_auth_wrap: BasicAuth
    lines: List[Line]
    payload: Payload
    output: ToFile


@dataclass
class Allhttp:
    allhttps: List[Http]
