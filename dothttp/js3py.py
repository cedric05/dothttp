import base64
import csv
import datetime
import hashlib
import math
import traceback
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
from faker import Faker


from . import MIME_TYPE_JSON, request_logger, ScriptType
from .utils import get_real_file_path

allowed_global = {
    '_print_': PrintCollector,
    "__metaclass__": type,
    "__name__": "test_script",
    "math": math,
    "hashlib": hashlib,
    "faker": Faker(),
    'unittest': unittest,
    'datetime': datetime,
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
    result: str = field(init=False)
    error: typing.Optional[str] = field(init=False)
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


def execute_script(script: str,
                   script_type: ScriptType.JAVA_SCRIPT,
                   resp: Response,
                   properties: typing.Dict[str, object],
                   ) -> ScriptResult:
    try:
        if not script:
            return ScriptResult(stdout="", error="", properties={}, tests=[])
        if script_type == ScriptType.PYTHON:
            log_func = PrintFunc()
            local = {}
            script_gloabal = dict(properties=properties,
                                  log=log_func, resp=resp, **allowed_global)
            byte_code = compile_restricted(script, 'test_script.py', 'exec')
            exec(byte_code, script_gloabal, local)
            script_result = ScriptResult(
                stdout="", error="", properties={}, tests=[])
            suite = unittest.TestSuite()
            unit_test_result = ScriptTestResult()
            unit_test_result.script_result(script_result)
            for key, func in local.items():
                if (key.startswith('test')):
                    if isinstance(func, types.FunctionType):
                        try:
                            test_result = TestResult(key)
                            try:
                                test_result.result = func()
                                test_result.success = True
                            except BaseException as e:
                                test_result.error = str(e)
                                test_result.success = False
                                request_logger.error(
                                    f"test execution failed {e}")
                            script_result.tests.append(test_result)
                        except:
                            pass
                elif issubclass(func, unittest.TestCase):
                    tests = unittest.TestLoader().loadTestsFromTestCase(func)
                    suite.addTests(tests)
            suite.run(unit_test_result)
            script_result.properties = properties
            script_result.stdout = log_func.get_script_output()
            return script_result
        else:
            # enable require will only be used for
            # those who want to use require in dothttp scripts
            # i will write up a document on how to do it
            context = js2py.EvalJs(enable_require=True)
            context.execute(js_template.replace("JS_CODE_REPLACE", script))
            content_type = resp.headers.get('content-type', 'text/plain')
            # in some cases mimetype can have charset
            # like text/plain; charset=utf-8
            content_type = content_type.split(
                ";")[0] if ';' in content_type else content_type
            client = context.jsHandler(
                content_type == MIME_TYPE_JSON, properties, resp.text, resp.status_code, dict(resp.headers))
            return get_test_results(client)
    except JsException as e:
        request_logger.error(f"js compile failed with error {e}")
        script_result = ScriptResult(
            stdout="", error="", properties={}, tests=[])
        script_result.compiled = False
        script_result.error = str(e)
    except Exception as e:
        traceback.print_exc()
    return script_result


def get_test_results(client):
    script_result = ScriptResult(stdout="", error="", properties={}, tests=[])
    for test_name in client.tests:
        test_result = TestResult(test_name)
        try:
            test_result.result = client.tests[test_name]()
            test_result.success = True
        except Exception as e:
            test_result.error = str(e)
            test_result.success = False
            request_logger.error(f"test execution failed {e}")
        script_result.tests.append(test_result)
    for i in client.properties.updated:
        if type(client.properties.vars[i]) != JsObjectWrapper:
            script_result.properties[i] = client.properties.vars[i] or ""
    script_result.stdout += "\n".join(client.stdout)
    return script_result
