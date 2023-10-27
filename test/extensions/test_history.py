import json
from typing import Union

from dotextensions.server.handlers.basic_handlers import ContentExecuteHandler
from dotextensions.server.models import Command
from test import TestBase


class HistoryValidate(TestBase):
    def setUp(self) -> None:
        self.execute_handler = ContentExecuteHandler()

    def execute_and_result(self,
                           content,
                           target: Union[str,
                                         int] = 1,
                           contexts=None,
                           curl=False):
        return self.execute_handler.run(Command(
            method=ContentExecuteHandler.name,
            params={
                "content": content,
                "properties": {
                    "post": "get"
                },
                "target": target,
                "contexts": contexts,
                "curl": curl
            },
            id=1)
        )

    def test_execute_content(self):
        result = self.execute_and_result(
            "GET http://localhost:8000/status/301")
        body = json.loads(result.result['body'])
        self.assertTrue("args" in body)
        self.assertTrue("headers" in body)
        self.assertEqual({}, body['args'])
        self.assertEqual("http://localhost:8000/get", body['url'])
        self.assertEqual(200, result.result['status'])
        self.assertTrue("history" in result.result)
        self.assertEqual(2, len(result.result['history']))
        self.assertEqual(301, result.result['history'][0]['status'])
        self.assertEqual(
            "http://localhost:8000/status/301",
            result.result['history'][0]['url'])
        self.assertEqual(302, result.result['history'][1]['status'])
        self.assertEqual(
            "http://localhost:8000/redirect/1",
            result.result['history'][1]['url'])
        print(result.result['history'])

    def test_execute_content2(self):
        result = self.execute_and_result(
            "GET http://localhost:8000/status/302")
        body = json.loads(result.result['body'])
        self.assertTrue("args" in body)
        self.assertTrue("headers" in body)
        self.assertEqual({}, body['args'])
        self.assertEqual("http://localhost:8000/get", body['url'])
        self.assertEqual(200, result.result['status'])
        self.assertTrue("history" in result.result)
        self.assertEqual(2, len(result.result['history']))
        self.assertEqual(302, result.result['history'][0]['status'])
        self.assertEqual(
            "http://localhost:8000/status/302",
            result.result['history'][0]['url'])
        self.assertEqual(302, result.result['history'][1]['status'])
        self.assertEqual(
            "http://localhost:8000/redirect/1",
            result.result['history'][1]['url'])
