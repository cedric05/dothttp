import json
import os
import unittest

from test import TestBase

from dotextensions.server.commands import *

dir_path = os.path.dirname(os.path.realpath(__file__))
command_dir = f"{dir_path}/commands"


class CommandTest(TestBase):

    def setUp(self) -> None:
        self.name_handler = GetNameReferencesHandler()

    def test_names(self):
        result = self.name_handler.run(Command(
            method=GetNameReferencesHandler.name,
            params={"file": f"{command_dir}/names.http"},
            id=1
        ))
        self.assertEqual({'names': [{'name': 'test', 'start': 0, 'end': 13}, {'name': 'test2', 'start': 79, 'end': 91},
                                    {'name': 'test3', 'start': 209, 'end': 221},
                                    {'name': 'test4.test', 'start': 339, 'end': 358}]},
                         result.result)

    def test_notexistant_file(self):
        result = self.name_handler.run(Command(
            method=GetNameReferencesHandler.name,
            params={"file": f"{command_dir}/names2.http"},
            id=1
        ))
        self.assertTrue(result.result['error'])

    def test_syntax_error_name(self):
        result = self.name_handler.run(Command(
            method=GetNameReferencesHandler.name,
            params={"file": f"{command_dir}/names_fail.http"},
            id=1
        ))
        self.assertTrue(result.result['error'])


class RunHandler(TestBase):
    def setUp(self) -> None:
        self.execute_handler = RunHttpFileHandler()

    def test_execute_file(self):
        result = self.execute_handler.run(Command(
            method=RunHttpFileHandler.name,
            params={
                "file": f"{command_dir}/simple.http"
            },
            id=1)
        )
        body = json.loads(result.result['body'])
        self.assertTrue("args" in body)
        self.assertTrue("headers" in body)
        self.assertEqual({}, body['args'])
        self.assertEqual("https://httpbin.org/get", body['url'])

    def test_complex_file(self):
        result = self.execute_handler.run(Command(
            method=RunHttpFileHandler.name,
            params={
                "file": f"{command_dir}/complexrun.http",
                "target": "2"
            },
            id=1)
        )
        body = json.loads(result.result['body'])
        self.assertTrue("status" in result.result)
        self.assertEqual(200, result.result["status"])
        self.assertTrue("headers" in result.result)
        self.assertEqual("https://httpbin.org/post?startusing=dothttp", body['url'])

        result2 = self.execute_handler.run(Command(
            method=RunHttpFileHandler.name,
            params={
                "file": f"{command_dir}/complexrun.http",
                "target": "2",
                "properties": {
                    "host": "req.dothttp.dev"
                }
            },
            id=1)
        )
        self.assertTrue("status" in result2.result)
        self.assertEqual(200, result2.result["status"])
        self.assertTrue("headers" in result2.result)
        self.assertEqual("https://httpbin.org/post?startusing=dothttp", body['url'])

        result3 = self.execute_handler.run(Command(
            method=RunHttpFileHandler.name,
            params={
                "file": f"{command_dir}/complexrun.http",
                "target": "3",
                "properties": {
                    "host": "req.dothttp.dev"
                }
            },
            id=1)
        )
        self.assertEqual(404, result3.result["status"])

    def test_non_existant_file(self):
        result = self.execute_file(f"{command_dir}/syntax2.http")
        self.assertEqual(True, result.result['error'])

    def test_syntax_issue_file(self):
        result = self.execute_file(f"{command_dir}/syntax.http")
        self.assertEqual(True, result.result['error'])

    def execute_file(self, filename, env=None, properties=None):
        if properties is None:
            properties = {}
        if env is None:
            env = []
        result = self.execute_handler.run(Command(
            method=RunHttpFileHandler.name,
            params={
                "file": filename,
                "env": env,
                "properties": properties
            },
            id=1)
        )
        return result

    def test_property_not_found(self):
        result = self.execute_file(f"{command_dir}/env.http")
        self.assertEqual(True, result.result['error'])

    def test_env(self):
        result = self.execute_file(f"{command_dir}/env.http", env=["simple"])
        self.assertEqual(200, result.result['status'])

    def test_property(self):
        result = self.execute_file(f"{command_dir}/env.http", properties={"path": "get"})
        self.assertEqual(200, result.result['status'])


if __name__ == '__main__':
    unittest.main()
