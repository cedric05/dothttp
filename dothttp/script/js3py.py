import base64
import csv
import datetime
import hashlib
import inspect
import json
import math
import types
import typing
import unittest
import urllib
import urllib.parse
import uuid
from dataclasses import dataclass, field
from operator import getitem

import cryptography
import xmltodict
import jsonschema
import requests
import yaml
from cryptography import *
from faker import Faker
from requests import Response
from requests.structures import CaseInsensitiveDict
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Eval import default_guarded_getiter
from RestrictedPython.Guards import guarded_iter_unpack_sequence
from RestrictedPython.PrintCollector import PrintCollector

from ..exceptions import DotHttpException, PreRequestScriptException, ScriptException
from ..parse import MIME_TYPE_JSON, HttpDef, request_logger
from ..utils.common import get_real_file_path
from ..utils.property_util import PropertyProvider



def write_guard(x):
    if isinstance(x, (Client, HttpDef, Properties, dict, list)):
        return x
    else:
        raise Exception("not allowed")


# def read_guard(x, attr):
#     return getattr(x, attr)


allowed_global = {
    "_print_": PrintCollector,
    "__metaclass__": type,
    "__name__": "test_script",
    "math": math,
    "type": type,
    "hashlib": hashlib,
    "faker": Faker(),
    "unittest": unittest,
    "datetime": datetime,
    "_write_": write_guard,
    "_getitem_": getitem,
    "_getiter_": default_guarded_getiter,
    "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
    "csv": csv,
    "uuid": uuid,
    "base64": base64,
    "urllib": urllib,
    "open": open,
    "json": json,
    "yaml": yaml,
    "cryptography": cryptography,
    "jsonschema": jsonschema,
    "requests": requests,
    "xmltodict": xmltodict,
}
allowed_global.update(safe_globals)



@dataclass
class TestResult:
    name: str
    result: typing.Union[None, str] = None
    error: typing.Union[None, str] = None
    success: bool = True


@dataclass
class ScriptResult:
    stdout: str
    error: str
    properties: typing.Dict[str, object]
    tests: typing.List[TestResult] = field(default_factory=lambda: [])
    compiled: bool = True

    def as_json(self):
        obj = vars(self)
        obj["tests"] = [vars(i) for i in self.tests]
        return obj


class PrintFunc:
    def __init__(self) -> None:
        self.script_output = ""

    def __call__(self, *args: typing.Any, **kwds: typing.Any) -> typing.Any:
        self.script_output += ", ".join([str(arg) for arg in args]) + "\n"

    def get_script_output(self):
        return self.script_output


class ScriptTestResult(unittest.TestResult):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def script_result(self, script_result):
        self.script_result: ScriptResult = script_result

    def addSuccess(self, test: unittest.case.TestCase) -> None:
        super().addSuccess(test)
        self.script_result.tests.append(TestResult(name=str(test), success=True))

    def addError(self, test: unittest.case.TestCase, err) -> None:
        super().addError(test, err)
        result = TestResult(str(test))
        result.success = False
        result.error = self._exc_info_to_string(err, test)
        self.script_result.tests.append(result)

    def addFailure(self, test: unittest.case.TestCase, err) -> None:
        super().addFailure(test, err)
        result = TestResult(str(test))
        result.success = False
        result.error = self._exc_info_to_string(err, test)
        self.script_result.tests.append(result)


class Properties(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.updated = {}

    def set(self, key, value):
        self.setdefault(key, value)
        self.updated[key] = value

    def clear(self, key):
        self.setdefault(key, "")

    def clear_all(self, key):
        for i in self:
            self.clear(key, "")


@dataclass
class _RequestInfo:
    method: typing.Union[None, str] = None
    url: typing.Union[None, str] = None
    headers: CaseInsensitiveDict = field(default_factory=CaseInsensitiveDict)


class DothttpResponse:
    """
    A ``requests.Response``-like adapter built from dothttp's serialized
    response format::

        {
            "body": <str | bytes>,           # or "body_base64": <str>
            "output_file": <str>,
            "headers": {<name>: <value>},
            "status": <int>,
            "method": <str>,
            "url": <str>,
            "request_headers": {<name>: <value>},   # optional
            "history": [<response dict>, ...],       # optional, redirect hops
        }

    It exposes the subset of the ``requests.Response`` surface that test
    scripts rely on (``status_code``, ``headers``, ``text``, ``content``,
    ``json()``, ``url``, ``ok``, ``request.method``, ``history`` ...), so
    tests can run against a previously captured response without re-issuing
    the request. ``history`` entries (redirect hops) are themselves
    ``DothttpResponse`` instances, mirroring ``requests``.
    """

    def __init__(self, data: dict):
        body = data.get("body", "")
        if isinstance(body, (bytes, bytearray)):
            self._content = bytes(body)
        elif data.get("body_base64"):
            self._content = base64.b64decode(data["body_base64"])
        else:
            self._content = (body or "").encode("utf-8")
        self.status_code = data.get("status", 0)
        self.headers = CaseInsensitiveDict(data.get("headers") or {})
        self.url = data.get("url", "")
        self.reason = data.get("reason", "")
        self.output_file = data.get("output_file", "")
        self.encoding = data.get("encoding") or self._guess_encoding()
        self.cookies = data.get("cookies", {})
        self.elapsed = datetime.timedelta(0)
        # redirect hops, each captured in the same serialized shape
        self.history = [
            DothttpResponse(hop) for hop in (data.get("history") or [])
        ]
        # the request that produced this response; a nested "request" dict
        # takes precedence, else fall back to the top-level method/url and
        # the "request_headers" emitted by the execute handlers
        request = data.get("request") or {}
        self.request = _RequestInfo(
            method=request.get("method", data.get("method")),
            url=request.get("url", data.get("url")),
            headers=CaseInsensitiveDict(
                request.get("headers") or data.get("request_headers") or {}
            ),
        )

    def _guess_encoding(self):
        content_type = (self.headers.get("content-type") or "").lower()
        if "charset=" in content_type:
            return content_type.split("charset=")[-1].split(";")[0].strip()
        return "utf-8"

    @property
    def content(self) -> bytes:
        return self._content

    @property
    def text(self) -> str:
        try:
            return self._content.decode(self.encoding or "utf-8", errors="replace")
        except (LookupError, TypeError):
            return self._content.decode("utf-8", errors="replace")

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def json(self, **kwargs):
        return json.loads(self.text, **kwargs)

    def iter_content(self, chunk_size=1, decode_unicode=False):
        content = self.text if decode_unicode else self._content
        for i in range(0, len(content), chunk_size):
            yield content[i : i + chunk_size]

    def raise_for_status(self):
        if 400 <= self.status_code:
            raise requests.HTTPError(
                f"{self.status_code} Error for url: {self.url}", response=self
            )

    def __repr__(self):
        return f"<DothttpResponse [{self.status_code}]>"


@dataclass
class Client:
    request: HttpDef
    properties: Properties
    env_properties: Properties
    infile_properties: Properties
    response: typing.Union[Response, "DothttpResponse"] = None


class ScriptExecutionEnvironmentBase:
    def __init__(self, httpdef: HttpDef, prop: PropertyProvider) -> None:
        self.client = Client(
            request=httpdef,
            properties=Properties(prop.get_all_properties_variables()),
            infile_properties={
                key: value.value for key, value in prop.infile_properties.items()
            },
            env_properties=dict(prop.env_properties),
        )

    def _init_request_script(self) -> None:
        pass

    def _pre_request_script(self) -> None:
        pass

    def _execute_test_script(self, resp: Response) -> ScriptResult:
        raise NotImplementedError()

    def init_request_script(self):
        try:
            self._init_request_script()
        except Exception as exc:
            request_logger.error("unknown exception happened", exc_info=True)
            raise PreRequestScriptException(payload=str(exc))

    def pre_request_script(self):
        try:
            self._pre_request_script()
        except PreRequestScriptException:
            raise
        except Exception as exc:
            request_logger.error("unknown exception happened", exc_info=True)
            raise PreRequestScriptException(payload=str(exc), function="''")

    def execute_test_script(self, resp) -> ScriptResult:
        if not self.client.request.test_script:
            return ScriptResult(stdout="", error="", properties={}, tests=[])
        try:
            return self._execute_test_script(resp)
        except DotHttpException as exc:
            request_logger.error(f"js/python compile failed with error {exc}")
            script_result = ScriptResult(stdout="", error="", properties={}, tests=[])
            script_result.compiled = False
            script_result.error = exc.message
            request_logger.error("unknown exception happened", exc_info=True)
            return script_result
        except Exception as exc:
            request_logger.error(f"js/python compile failed with error {exc}")
            script_result = ScriptResult(stdout="", error="", properties={}, tests=[])
            script_result.compiled = False
            script_result.error = str(exc)
            request_logger.error("unknown exception happened", exc_info=True)
            return script_result


class ScriptExecutionPython(ScriptExecutionEnvironmentBase):
    def __init__(self, httpdef: HttpDef, prop: PropertyProvider) -> None:
        super().__init__(httpdef, prop)
        self.log_func = PrintFunc()
        self.local = {}
        script_gloabal = dict(log=self.log_func, client=self.client, **allowed_global)
        try:
            byte_code = compile_restricted(
                self.client.request.test_script, "test_script.py", "exec"
            )
            exec(byte_code, script_gloabal, self.local)
        except Exception as exc:
            raise ScriptException(payload=str(exc), function="test_script.py")

    def _init_request_script(self) -> None:
        # just for variables initialization
        for key, func in self.local.items():
            if (key.startswith("init")) and isinstance(func, types.FunctionType):
                func()

    def _pre_request_script(self) -> None:
        for key, pre_request_func in self.local.items():
            if (key.startswith("pre")) and isinstance(pre_request_func, types.FunctionType):
                try:
                    pre_request_func()
                except Exception as exc:
                    request_logger.error(f"pre request script failed {exc}")
                    raise PreRequestScriptException(function=key, payload=str(exc))

    def _execute_test_script(self, resp: Response) -> ScriptResult:
        script_result = ScriptResult(stdout="", error="", properties={}, tests=[])
        suite = unittest.TestSuite()
        unit_test_result = ScriptTestResult()
        unit_test_result.script_result(script_result)
        self.client.response = resp
        for key, func in self.local.items():
            if key.startswith("test"):
                if isinstance(func, types.FunctionType):
                    test_result = TestResult(key)
                    try:
                        test_result.result = func()
                        test_result.success = True
                    except BaseException as exc:
                        test_result.error = f"\n\nTest function with name `{key}` failed with error `{exc}`\n\n"
                        test_result.success = False
                        request_logger.error(f"test execution failed {exc}")
                    script_result.tests.append(test_result)
            elif inspect.isclass(func) and issubclass(func, unittest.TestCase):
                tests = unittest.TestLoader().loadTestsFromTestCase(func)
                suite.addTests(tests)
        suite.run(unit_test_result)
        script_result.properties = self.client.properties.updated
        script_result.stdout = self.log_func.get_script_output()
        return script_result
