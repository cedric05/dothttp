from dataclasses import dataclass
from typing import Optional, List, Any

from ..utils import from_str, from_none, from_union, from_list, to_class


@dataclass
class NameValueComment:
    name: Optional[str] = None
    value: Optional[str] = None
    comment: Optional[str] = None

    def to_dict(self) -> dict:
        result: dict = {}
        result["name"] = from_union([from_str, from_none], self.name)
        result["value"] = from_union([from_str, from_none], self.value)
        result["comment"] = from_union([from_str, from_none], self.comment)
        return result


class QueryString(NameValueComment):
    @staticmethod
    def from_dict(obj: Any) -> 'QueryString':
        assert isinstance(obj, dict)
        name = from_union([from_str, from_none], obj.get("name"))
        value = from_union([from_str, from_none], obj.get("value"))
        comment = from_union([from_str, from_none], obj.get("comment"))
        return QueryString(name, value, comment)


class Header(NameValueComment):
    @staticmethod
    def from_dict(obj: Any) -> 'Header':
        assert isinstance(obj, dict)
        name = from_union([from_str, from_none], obj.get("name"))
        value = from_union([from_str, from_none], obj.get("value"))
        comment = from_union([from_str, from_none], obj.get("comment"))
        return Header(name, value, comment)


@dataclass
class Param:
    name: Optional[str] = None
    value: Optional[str] = None
    fileName: Optional[str] = None
    contentType: Optional[str] = None
    comment: Optional[str] = None

    @staticmethod
    def from_dict(obj: Any) -> 'Param':
        assert isinstance(obj, dict)
        name = from_union([from_str, from_none], obj.get("name"))
        value = from_union([from_str, from_none], obj.get("value"))
        fileName = from_union([from_str, from_none], obj.get("fileName"))
        contentType = from_union([from_str, from_none], obj.get("contentType"))
        comment = from_union([from_str, from_none], obj.get("comment"))
        return Param(name, value, fileName, contentType, comment)

    def to_dict(self) -> dict:
        result: dict = {}
        result["name"] = from_union([from_str, from_none], self.name)
        result["value"] = from_union([from_str, from_none], self.value)
        result["fileName"] = from_union([from_str, from_none], self.fileName)
        result["contentType"] = from_union([from_str, from_none], self.contentType)
        result["comment"] = from_union([from_str, from_none], self.comment)
        return result


@dataclass
class PostData:
    mimeType: Optional[str] = None
    params: Optional[List[Param]] = None
    text: Optional[str] = None
    comment: Optional[str] = None

    @staticmethod
    def from_dict(obj: Any) -> 'PostData':
        assert isinstance(obj, dict)
        mimeType = from_union([from_str, from_none], obj.get("mimeType"))
        params = from_union([lambda x: from_list(Param.from_dict, x), from_none], obj.get("params"))
        text = from_union([from_str, from_none], obj.get("text"))
        comment = from_union([from_str, from_none], obj.get("comment"))
        return PostData(mimeType, params, text, comment)

    def to_dict(self) -> dict:
        result: dict = {}
        result["mimeType"] = from_union([from_str, from_none], self.mimeType)
        result["params"] = from_union([lambda x: from_list(lambda x: to_class(Param, x), x), from_none], self.params)
        result["text"] = from_union([from_str, from_none], self.text)
        result["comment"] = from_union([from_str, from_none], self.comment)
        return result


@dataclass
class HarRequest:
    method: str = None
    url: str = None
    httpVersion: Optional[str] = None
    headers: Optional[List[Header]] = None
    queryString: Optional[List[QueryString]] = None
    postData: Optional[PostData] = None
    comment: Optional[str] = None

    @staticmethod
    def from_dict(obj: Any) -> 'HarRequest':
        assert isinstance(obj, dict)
        method = from_union([from_str, from_none], obj.get("method"))
        url = from_union([from_str, from_none], obj.get("url"))
        httpVersion = from_union([from_str, from_none], obj.get("httpVersion"))
        headers = from_union([lambda x: from_list(Header.from_dict, x), from_none], obj.get("headers"))
        queryString = from_union([lambda x: from_list(QueryString.from_dict, x), from_none], obj.get("queryString"))
        postData = from_union([PostData.from_dict, from_none], obj.get("postData"))
        comment = from_union([from_str, from_none], obj.get("comment"))
        return HarRequest(method, url, httpVersion, headers, queryString, postData, comment)

    def to_dict(self) -> dict:
        result: dict = {}
        result["method"] = from_union([from_str, from_none], self.method)
        result["url"] = from_union([from_str, from_none], self.url)
        result["httpVersion"] = from_union([from_str, from_none], self.httpVersion)
        result["headers"] = from_union([lambda x: from_list(lambda x: to_class(Header, x), x), from_none], self.headers)
        result["queryString"] = from_union([lambda x: from_list(lambda x: to_class(Header, x), x), from_none],
                                           self.queryString)
        result["comment"] = from_union([from_str, from_none], self.comment)
        result["postData"] = from_union([lambda x: to_class(PostData, x), from_none], self.postData)
        return result


@dataclass
class Entry:
    request: Optional[HarRequest] = None

    @staticmethod
    def from_dict(obj: Any) -> 'Entry':
        assert isinstance(obj, dict)
        request = from_union([HarRequest.from_dict, from_none], obj.get("request"))
        return Entry(request)

    def to_dict(self) -> dict:
        result: dict = {}
        result["request"] = from_union([lambda x: to_class(HarRequest, x), from_none], self.request)
        return result


@dataclass
class Log:
    entries: Optional[List[Entry]] = None

    @staticmethod
    def from_dict(obj: Any) -> 'Log':
        assert isinstance(obj, dict)
        entries = from_union([lambda x: from_list(Entry.from_dict, x), from_none], obj.get("entries"))
        return Log(entries)

    def to_dict(self) -> dict:
        result: dict = {}
        result["entries"] = from_union([lambda x: from_list(lambda x: to_class(Entry, x), x), from_none], self.entries)
        return result


@dataclass
class Har:
    log: Optional[Log] = None

    @staticmethod
    def from_dict(obj: Any) -> 'Har':
        assert isinstance(obj, dict)
        log = from_union([Log.from_dict, from_none], obj.get("log"))
        return Har(log)

    def to_dict(self) -> dict:
        result: dict = {}
        result["log"] = from_union([lambda x: to_class(Log, x), from_none], self.log)
        return result


def Harfromdict(s: Any) -> Har:
    return Har.from_dict(s)
