import os
import sys

from dotextensions.server import Command
from dotextensions.server.commands import ParseHttpData
from test import TestBase
from test.extensions.test_commands import command_dir

dir_path = os.path.dirname(os.path.realpath(__file__))
fixtures_dir = f"{dir_path}/fixtures"


class ToHar(TestBase):
    def setUp(self) -> None:
        self.maxDiff = None
        self.execute_handler = ParseHttpData()

    def test_error(self):
        command = Command(
            method=ParseHttpData.name,
            params={
                "file": f"{command_dir}/syntax.http",
                "target": "3",
                "properties": {
                    "host": "httpbin.org"
                }
            },
            id=1)
        result = self.execute_handler.run(command=command)
        self.assertTrue(result.result["error"])

    def test_basic_file(self):
        self.basic_test(file=f"{command_dir}/simple.http", content=None)

    def test_basic_content(self):
        self.basic_test(file=None, content="GET https://{{host=httpbin.org}}/get")

    def basic_test(self, **kwargs):
        command = Command(
            method=ParseHttpData.name,
            params={
                "content": kwargs['content'],
                "file": kwargs['file'],
                "target": "1",
                "properties": {
                    "host": "httpbin.org"
                }
            },
            id=1)
        result = self.execute_handler.run(command=command)
        self.assertFalse(result.result.get("error", False))
        self.assertEqual({'target': {'1': {'headers': [],
                                           'method': 'GET',
                                           'payload': {'mimeType': None},
                                           'query': [],
                                           'url': 'https://httpbin.org/get'}}}, result.result)

    def test_content_target(self):
        self.complex_test(file=f"{command_dir}/complexrun.http", content=None)

    def test_complex_body(self):
        with open(f"{command_dir}/complexrun.http") as f:
            content = f.read()
        self.complex_test(file=None, content=content)

    def complex_test(self, **kwargs):
        command = Command(
            method=ParseHttpData.name,
            params={
                "file": f"{command_dir}/complexrun.http",
                "target": "1",
                "properties": {
                    "host": "httpbin.org"
                }
            },
            id=1)
        result1 = self.execute_handler.run(command=command)
        self.assertFalse(result1.result.get("error", False))
        self.assertEqual({'target': {'1': {'headers': [],
                                           'method': 'GET',
                                           'payload': {'mimeType': None},
                                           'query': [{'name': 'dothttp', 'value': 'rocks'}],
                                           'url': 'https://httpbin.org/get'}}}, result1.result)
        command.params['target'] = "2"
        result2 = self.execute_handler.run(command=command)
        self.assertFalse(result2.result.get("error", False))
        self.assertEqual({'target': {'2': {'headers': [],
                                           'method': 'POST',
                                           'payload': {'mimeType': None},
                                           'query': [{'name': 'startusing', 'value': 'dothttp'}],
                                           'url': 'https://httpbin.org/post'}}}, result2.result)

    def test_payload_file(self):
        filename = f"{command_dir}/payload.http"
        self.payload_test(file=filename)

    def test_payload_content(self):
        filename = f"{command_dir}/payload.http"
        with open(filename) as f:
            self.payload_test(content=f.read())

    def payload_test(self, **kwargs):
        self.assertEqual({'target': {'json': {'headers': [],
                                              'method': 'POST',
                                              'payload': {'mimeType': 'application/json',
                                                          'text': '{"paylaod": "json"}'},
                                              'query': [],
                                              'url': 'https://req.dothttp.dev'}}},
                         self.execute_payload(target='json', **kwargs).result)
        self.assertEqual({'target': {'urlencode': {'headers': [],
                                                   'method': 'POST',
                                                   'payload': {'mimeType': 'application/x-www-form-urlencoded',
                                                               'text': 'paylaod=json'},
                                                   'query': [],
                                                   'url': 'https://req.dothttp.dev'}}},
                         self.execute_payload(target='urlencode', **kwargs).result)
        self.assertEqual({'target': {'text-other-content': {'headers': [],
                                                            'method': 'POST',
                                                            'payload': {'mimeType': 'other-content-type',
                                                                        'text': 'raw data'},
                                                            'query': [],
                                                            'url': 'https://req.dothttp.dev'}}},
                         self.execute_payload(target='text-other-content', **kwargs).result)
        mimetype = 'application/octet-stream' if sys.platform.startswith("win32") else 'text/plain'
        self.assertEqual({'target': {'files': {'headers': [],
                                               'method': 'POST',
                                               'payload': {'mimeType': 'multipart/form-data',
                                                           'params': [{'contentType': mimetype,
                                                                       'fileName': None,
                                                                       'name': 'raw data',
                                                                       'value': 'other-content-type'},
                                                                      {'contentType': mimetype,
                                                                       'fileName': None,
                                                                       'name': 'raw data',
                                                                       'value': 'other-content-type'}]},
                                               'query': [],
                                               'url': 'https://req.dothttp.dev'}}},
                         self.execute_payload(target='files', **kwargs).result)
        linux = {'target': {'text': {'headers': [],
                                     'method': 'POST',
                                     'payload': {'mimeType': mimetype,
                                                 'text': 'raw data'},
                                     'query': [],
                                     'url': 'https://req.dothttp.dev'}}}
        self.assertEqual(linux,
                         self.execute_payload(target='text', **kwargs).result)
        filename = f"{command_dir}/payload.http"
        self.assertEqual({'target': {'files2': {'headers': [],
                                                'method': 'POST',
                                                'payload': {'mimeType': 'multipart/form-data',
                                                            'params': [{'contentType': 'text/plain',
                                                                        'fileName': filename,
                                                                        'name': 'file',
                                                                        'value': None}]},
                                                'query': [],
                                                'url': 'https://req.dothttp.dev'}}},
                         self.execute_payload(target='files2', **kwargs).result)

    def test_headers_file(self):
        filename = f"{command_dir}/payload.http"
        self.assertEqual({'target': {'headers': {'headers': [{'name': 'key', 'value': 'value'},
                                                             {'name': 'key2', 'value': 'value'}],
                                                 'method': 'POST',
                                                 'payload': {'mimeType': None},
                                                 'query': [],
                                                 'url': 'https://req.dothttp.dev'}}},
                         self.execute_payload(target='headers', file=filename).result)

    def execute_payload(self, **kwargs):
        kwargs["properties"] = {"filename": os.path.join(dir_path, f"{command_dir}/payload.http")}
        command = Command(
            method=ParseHttpData.name,
            params=kwargs,
            id=1)
        result = self.execute_handler.run(command=command)
        self.assertFalse(result.result.get("error", False))
        return result
