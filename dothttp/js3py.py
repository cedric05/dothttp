import typing
from dataclasses import dataclass, field

import js2py
from js2py.base import JsObjectWrapper
from js2py.internals.simplex import JsException

from . import request_logger
from .utils import get_real_file_path

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


def execute_script(is_json: bool, properties: typing.Dict[str, object],
                   response_body_text: str, status_code: int,
                   headers: typing.Dict[str, str], script: str) -> ScriptResult:
    try:
        if not script:
            return ScriptResult(stdout="", error="", properties={}, tests=[])
        # enable require will only be used for
        # those who want to use require in dothttp scripts
        # i will write up a document on how to do it
        context = js2py.EvalJs(enable_require=True)
        context.execute(js_template.replace("JS_CODE_REPLACE", script))
        client = context.jsHandler(is_json, properties, response_body_text, status_code, headers)
        return get_test_results(client)
    except JsException as e:
        request_logger.error(f"js compile failed with error {e}")
        script_result = ScriptResult(stdout="", error="", properties={}, tests=[])
        script_result.compiled = False
        script_result.error = str(e)
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
