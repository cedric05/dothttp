import json

from dotextensions.server import Command
from dotextensions.server.commands import ContentExecuteHandler
from test import TestBase


class FileExecute(TestBase):
    def setUp(self) -> None:
        self.execute_handler = ContentExecuteHandler()

    def test_execute_content(self):
        result = self.execute_and_result("GET https://httpbin.org/get")
        self.compare_results(result, "https://httpbin.org/get")

    def compare_results(self, result, url):
        body = json.loads(result.result['body'])
        self.assertTrue("args" in body)
        self.assertTrue("headers" in body)
        self.assertEqual({}, body['args'])
        self.assertEqual(url, body['url'])
        self.assertEqual(200, result.result['status'])

    def test_405_execute_content(self):
        result = self.execute_and_result("GET https://httpbin.org/post")
        self.assertEqual(405, result.result['status'])

    def execute_and_result(self, content):
        return self.execute_handler.run(Command(
            method=ContentExecuteHandler.name,
            params={
                "content": content,
                "properties": {
                    "post": "get"
                }
            },
            id=1)
        )

    def test_fail_syntax(self):
        result = self.execute_and_result("GET2 https://httpbin.org/post")
        self.assertEqual(True, result.result['error'])

    def test_properties(self):
        """env doesnt live as it has no relative .dothttp.json path"""
        result = self.execute_and_result("GET https://httpbin.org/{{post}}")
        self.compare_results(result, "https://httpbin.org/get")
