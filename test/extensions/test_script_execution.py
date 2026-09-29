import os
from test import TestBase
from typing import Dict
from unittest import skip

from dotextensions.server.handlers.basic_handlers import (
    ContentTestHandler,
    RunHttpFileHandler,
    RunHttpFileTestHandler,
)
from dotextensions.server.models import Command

dir_path = os.path.dirname(os.path.realpath(__file__))
command_dir = f"{dir_path}/commands"


class ScriptExecutionTest(TestBase):
    def setUp(self) -> None:
        self.execute_handler = RunHttpFileHandler()

    def test_execute_script1(self):
        result = self.execute_target("1")
        script_result = result.result["script_result"]
        self.assertEqual(True, script_result["compiled"])
        self.assertEqual("", script_result["error"])
        self.assertEqual({"outputval": "User-agent: *\nDisallow: /deny\n"}, script_result["properties"])
        self.assertEqual("", script_result["stdout"])
        self.assertEqual(2, len(script_result["tests"]))
        # Check that we have test_content_type and test_status tests
        test_names = {test["name"] for test in script_result["tests"]}
        self.assertTrue(any("test_content_type" in name for name in test_names))
        self.assertTrue(any("test_status" in name for name in test_names))
        # One test should pass (status), one should fail (content_type)
        success_count = sum(1 for test in script_result["tests"] if test["success"])
        self.assertEqual(1, success_count)

    def test_execute_script2(self):
        result = self.execute_target("2")
        script_result = result.result["script_result"]
        self.assertEqual(True, script_result["compiled"])
        self.assertEqual("", script_result["error"])
        self.assertEqual({"outputval": "secret_token"}, script_result["properties"])
        self.assertEqual("this is sample log\n", script_result["stdout"])
        self.assertEqual(2, len(script_result["tests"]))
        # Both tests should pass
        for test in script_result["tests"]:
            self.assertTrue(test["success"])
            self.assertIsNone(test["error"])

    def test_execute_is_equals_script3(self):
        result = self.execute_target("3")
        script_result = result.result["script_result"]
        self.assertEqual(True, script_result["compiled"])
        self.assertEqual("", script_result["error"])
        self.assertEqual({}, script_result["properties"])
        self.assertEqual("", script_result["stdout"])
        self.assertEqual(1, len(script_result["tests"]))
        # The test should pass
        self.assertTrue(script_result["tests"][0]["success"])
        self.assertIsNone(script_result["tests"][0]["error"])

    def test_execute_delete_property_script(self):
        value = "this is before"
        result = self.execute_target(
            "delete property", properties={"setPropertyByfile": value}
        )
        self.assertEqual(
            {
                "compiled": True,
                "error": "",
                "properties": {"setPropertyByfile": ""},
                "stdout": f"value is `{value}`\n",
                "tests": [{'error': None, 'name': 'test_1', 'result': None, 'success': True}],
            },
            result.result["script_result"],
        )

    def test_execute_error(self):
        result = self.execute_target(
            "script error",
        )
        script_result = result.result["script_result"]
        self.assertEqual(True, script_result["compiled"])
        # The script compiles but will have an error in stdout (KeyError)
        self.assertEqual({}, script_result["properties"])
        self.assertEqual([{'error': '\n'
  '\n'
  'Test function with name `test_1` failed with error `Expecting '
  'value: line 1 column 1 (char 0)`\n'
  '\n',
  'name': 'test_1',
  'result': None,
  'success': False}]
, script_result["tests"])

    def execute_target(self, target, properties=None):
        if properties is None:
            properties = {}
        result = self.execute_handler.run(
            Command(
                method=RunHttpFileHandler.name,
                params={
                    "file": f"{command_dir}/script.http",
                    "target": target,
                    "properties": properties,
                },
                id=1,
            )
        )
        return result


class TestOnlyExecutionTest(TestBase):
    """
    Tests the tests-only handlers (`/file/test`, `/content/test`) that run the
    test script against a previously-captured response, without issuing a new
    HTTP request.
    """

    def setUp(self) -> None:
        self.file_handler = RunHttpFileTestHandler()
        self.content_handler = ContentTestHandler()

    def test_file_tests_pass_against_captured_response(self):
        # target "1" (text payload) asserts status==200 and
        # content-type=="application/json", and stores response.text
        result = self.run_file_target(
            "1",
            response={
                "body": "hello world",
                "output_file": "",
                "headers": {"content-type": "application/json"},
                "status": 200,
                "method": "GET",
                "url": "http://localhost:8000/robots.txt",
            },
        )
        script_result = result.result["script_result"]
        self.assertEqual(True, script_result["compiled"])
        self.assertEqual({"outputval": "hello world"}, script_result["properties"])
        self.assertEqual(2, len(script_result["tests"]))
        for test in script_result["tests"]:
            self.assertTrue(test["success"], test["error"])
        # no request was made
        self.assertEqual("GET", result.result["method"])

    def test_file_tests_report_failure(self):
        # a non-json content-type makes test_content_type fail while
        # test_status still passes
        result = self.run_file_target(
            "1",
            response={
                "body": "hello world",
                "output_file": "",
                "headers": {"content-type": "text/plain"},
                "status": 200,
                "method": "GET",
                "url": "http://localhost:8000/robots.txt",
            },
        )
        script_result = result.result["script_result"]
        self.assertEqual(True, script_result["compiled"])
        success_count = sum(1 for t in script_result["tests"] if t["success"])
        self.assertEqual(1, success_count)

    def test_json_body_is_parsed(self):
        # target "2" reads response.json()["json"]["token"] into a property
        result = self.run_file_target(
            "2",
            response={
                "body": '{"json": {"token": "secret_token"}}',
                "output_file": "",
                "headers": {"content-type": "application/json"},
                "status": 200,
                "method": "POST",
                "url": "http://localhost:8000/post",
            },
        )
        script_result = result.result["script_result"]
        self.assertEqual({"outputval": "secret_token"}, script_result["properties"])
        self.assertEqual("this is sample log\n", script_result["stdout"])
        for test in script_result["tests"]:
            self.assertTrue(test["success"], test["error"])

    def test_content_handler_with_history_and_request(self):
        content = """
GET http://localhost:8000/get
> {%
def test_history():
    assert len(client.response.history) == 1
    assert client.response.history[0].status_code == 302

def test_request():
    assert client.response.request.method == "GET"

def test_status():
    assert client.response.status_code == 200
%} python
"""
        result = self.content_handler.run(
            Command(
                method=ContentTestHandler.name,
                params={
                    "content": content,
                    "response": {
                        "body": "{}",
                        "output_file": "",
                        "headers": {"content-type": "application/json"},
                        "status": 200,
                        "method": "GET",
                        "url": "http://localhost:8000/get",
                        "request": {
                            "method": "GET",
                            "url": "http://localhost:8000/redirect",
                            "headers": {},
                        },
                        "history": [
                            {
                                "status": 302,
                                "headers": {"location": "http://localhost:8000/get"},
                                "method": "GET",
                                "url": "http://localhost:8000/redirect",
                            }
                        ],
                    },
                },
                id=1,
            )
        )
        script_result = result.result["script_result"]
        self.assertEqual(True, script_result["compiled"])
        self.assertEqual(3, len(script_result["tests"]))
        for test in script_result["tests"]:
            self.assertTrue(test["success"], test["error"])

    def run_file_target(self, target, response, properties=None):
        if properties is None:
            properties = {}
        return self.file_handler.run(
            Command(
                method=RunHttpFileTestHandler.name,
                params={
                    "file": f"{command_dir}/script.http",
                    "target": target,
                    "properties": properties,
                    "response": response,
                },
                id=1,
            )
        )
