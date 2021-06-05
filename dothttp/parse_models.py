from dataclasses import dataclass, field
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
class DigestAuth:
    username: str
    password: str


@dataclass
class AuthWrap:
    # digest = DIGESTAUTH | basicauth = BASICAUTH
    digest_auth: Optional[DigestAuth] = None
    basic_auth: Optional[BasicAuth] = None


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
class TripleOrDouble:
    triple: Optional[str] = None
    str: Optional[str] = None


@dataclass
class Payload:
    data: Optional[List[TripleOrDouble]]
    datajson: Optional
    file: Optional[str]
    json: Optional
    fileswrap: Optional[FilesWrap]
    type: Optional[str]
    multi: Optional[str] = None


@dataclass
class ToFile:
    output: str


@dataclass
class TestScript:
    script: Optional[str]


@dataclass
class Http:
    namewrap: Optional[NameWrap]
    urlwrap: UrlWrap
    authwrap: Optional[AuthWrap]
    lines: Optional[List[Line]]
    payload: Optional[Payload]
    output: Optional[ToFile]
    script_wrap: Optional[TestScript] = field(default_factory=lambda: TestScript(''))


@dataclass
class Allhttp:
    allhttps: List[Http]
