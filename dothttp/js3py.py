import base64
import csv
import datetime
import hashlib
import inspect
import math
import types
import typing
from dataclasses import dataclass, field
import unittest
import uuid

import js2py
from js2py.base import JsObjectWrapper
from js2py.internals.simplex import JsException
from requests import Response

from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.PrintCollector import PrintCollector
from RestrictedPython.Guards import guarded_iter_unpack_sequence
from RestrictedPython.Eval import default_guarded_getiter

from operator import getitem
from faker import Faker

from dothttp.exceptions import DotHttpException, PreRequestScriptException, ScriptException


from .property_util import PropertyProvider
from . import MIME_TYPE_JSON, HttpDef, request_logger
from .utils import get_real_file_path


def write_guard(x):
    if isinstance(x, Client):
        return x
    else:
        raise Exception("not allowed")

# def read_guard(x, attr):
#     return getattr(x, attr)


allowed_global = {
    '_print_': PrintCollector,
    "__metaclass__": type,
    "__name__": "test_script",
    "math": math,
    "hashlib": hashlib,
    "faker": Faker(),
    'unittest': unittest,
    'datetime': datetime,
    '_write_': write_guard,
    "_getitem_": getitem,
    "_getiter_" : default_guarded_getiter,
    "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
    'csv': csv,
    'uuid': uuid,
    'base64': base64,
}
allowed_global.update(safe_globals)

# disable python imports
# js2py.disable_pyimport() # so that few libraries can be imported

with open(get_real_file_path("postScript.js", __file__)) as f:
    js_template = f.read()


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
        obj['tests'] = [vars(i) for i in self.tests]
        return obj


class PrintFunc():
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
        self.script_result.tests.append(
            TestResult(name=str(test), success=True))

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
        self.setdefault(key, '')

    def clear_all(self, key):
        for i in self:
            self.clear(key, '')


@dataclass
class Client:
    request: HttpDef
    properties: Properties
    response: Response = None


class ScriptExecutionEnvironmentBase:
    def __init__(self, httpdef: HttpDef, prop: PropertyProvider) -> None:
        self.client = Client(
            request=httpdef, properties=Properties(prop.get_all_properties_variables()))

    def _pre_request_script(self) -> None:
        pass

    def _execute_test_script(self, resp: Response) -> ScriptResult:
        raise NotImplementedError()

    def pre_request_script(self):
        try:
            self._pre_request_script()
        except Exception as exc:
            request_logger.error("unknown exception happened", exc_info=True)
            raise PreRequestScriptException(payload=str(exc))

    def execute_test_script(self, resp):
        if not self.client.request.test_script:
            return ScriptResult(
                stdout="", error="", properties={}, tests=[])
        try:
            return self._execute_test_script(resp)
        except DotHttpException as exc:
            request_logger.error(f"js/python compile failed with error {exc}")
            script_result = ScriptResult(
                stdout="", error="", properties={}, tests=[])
            script_result.compiled = False
            script_result.error = exc.message
            request_logger.error("unknown exception happened", exc_info=True)
            return script_result
        except Exception as exc:
            request_logger.error(f"js/python compile failed with error {exc}")
            script_result = ScriptResult(
                stdout="", error="", properties={}, tests=[])
            script_result.compiled = False
            script_result.error = str(exc)
            request_logger.error("unknown exception happened", exc_info=True)
            return script_result


class ScriptExecutionJs(ScriptExecutionEnvironmentBase):

    def _execute_test_script(self, resp) -> None:
        # enable require will only be used for
        # those who want to use require in dothttp scripts
        # i will write up a document on how to do it
        context = js2py.EvalJs(enable_require=True)
        try:
            context.execute(js_template.replace(
                "JS_CODE_REPLACE", self.client.request.test_script))
        except JsException as exc:
            raise ScriptException(payload=str(exc))
        content_type = resp.headers.get('content-type', 'text/plain')
        # in some cases mimetype can have charset
        # like text/plain; charset=utf-8
        content_type = content_type.split(
            ";")[0] if ';' in content_type else content_type
        client = context.jsHandler(
            content_type == MIME_TYPE_JSON, self.client.properties, resp.text, resp.status_code, dict(resp.headers))
        script_result = ScriptResult(
            stdout="", error="", properties={}, tests=[])
        for test_name in client.tests:
            test_result = TestResult(test_name)
            try:
                test_result.result = client.tests[test_name]()
                test_result.success = True
            except Exception as exc:
                test_result.error = str(exc)
                test_result.success = False
                request_logger.error(f"test execution failed {exc}")
            script_result.tests.append(test_result)
        for i in client.properties.updated:
            if type(client.properties.vars[i]) != JsObjectWrapper:
                script_result.properties[i] = client.properties.vars[i] or ""
        script_result.stdout += "\n".join(client.stdout)
        return script_result


class ScriptExecutionPython(ScriptExecutionEnvironmentBase):

    def __init__(self, httpdef: HttpDef, prop: PropertyProvider) -> None:
        super().__init__(httpdef, prop)
        self.log_func = PrintFunc()
        self.local = {}
        script_gloabal = dict(
            log=self.log_func, client=self.client, **allowed_global)
        try:
            byte_code = compile_restricted(
                self.client.request.test_script, 'test_script.py', 'exec')
            exec(byte_code, script_gloabal, self.local)
        except Exception as exc:
            raise ScriptException(payload=str(exc))

    def _pre_request_script(self) -> None:
        for key, func in self.local.items():
            if (key.startswith('pre')) and isinstance(func, types.FunctionType):
                func()

    def _execute_test_script(self, resp: Response) -> ScriptResult:
        script_result = ScriptResult(
            stdout="", error="", properties={}, tests=[])
        suite = unittest.TestSuite()
        unit_test_result = ScriptTestResult()
        unit_test_result.script_result(script_result)
        self.client.response = resp
        for key, func in self.local.items():
            if (key.startswith('test')):
                if isinstance(func, types.FunctionType):
                    test_result = TestResult(key)
                    try:
                        test_result.result = func()
                        test_result.success = True
                    except BaseException as exc:
                        test_result.error = str(exc)
                        test_result.success = False
                        request_logger.error(
                            f"test execution failed {exc}")
                    script_result.tests.append(test_result)
            elif inspect.isclass(func) and issubclass(func, unittest.TestCase):
                tests = unittest.TestLoader().loadTestsFromTestCase(func)
                suite.addTests(tests)
        suite.run(unit_test_result)
        script_result.properties = self.client.properties.updated
        script_result.stdout = self.log_func.get_script_output()
        return script_result
