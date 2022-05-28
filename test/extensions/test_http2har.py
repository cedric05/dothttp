import os
import sys
import tempfile

from dotextensions.server.handlers.http2har import Http2Har
from dotextensions.server.models import Command
from test import TestBase
from test.extensions.test_commands import command_dir

dir_path = os.path.dirname(os.path.realpath(__file__))
fixtures_dir = f"{dir_path}/fixtures"


class ToHarTest(TestBase):
    def setUp(self) -> None:
        self.maxDiff = None
        self.execute_handler = Http2Har()

    def test_error(self):
        command = Command(
            method=Http2Har.name,
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
        self.basic_test(
            file=None, content="GET https://{{host=httpbin.org}}/get")

    def basic_test(self, **kwargs):
        command = Command(
            method=Http2Har.name,
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
                                           'payload': {},
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
            method=Http2Har.name,
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
                                           'payload': {},
                                           'query': [{'name': 'dothttp', 'value': 'rocks'}],
                                           'url': 'https://httpbin.org/get'}}}, result1.result)
        command.params['target'] = "2"
        result2 = self.execute_handler.run(command=command)
        self.assertFalse(result2.result.get("error", False))
        self.assertEqual({'target': {'2': {'headers': [],
                                           'method': 'POST',
                                           'payload': {},
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
        mimetype = 'application/octet-stream' if sys.platform.startswith(
            "win32") else 'text/plain'
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
                                                 'payload': {},
                                                 'query': [],
                                                 'url': 'https://req.dothttp.dev'}}},
                         self.execute_payload(target='headers', file=filename).result)

    def test_basicauth(self):
        filename = f"{command_dir}/urlquery.http"
        self.assertEqual({'target': {'basic auth': {'headers': [{'name': 'Authorization',
                                                                 'value': 'Basic Zm9vOmJhcg=='}],
                                                    'method': 'GET',
                                                    'payload': {},
                                                    'query': [],
                                                    'url': 'http://httpbin.org/basic-auth/foo/bar'}}},
                         self.execute_payload(target='basic auth', file=filename).result)

    def test_payloadfileinput(self):
        filename = f"{command_dir}/fileinput.http"
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hai")
            f.flush()
            self.assertEqual({'target': {'fileinput': {'headers': [],
                                                       'method': 'POST',
                                                       'payload': {'mimeType': 'text/plain', 'text': 'hai'},
                                                       'query': [],
                                                       'url': 'https://req.dothttp.dev'}}},
                             self.execute_payload(target='fileinput', file=filename, fileinputarg=f.name).result)

    def test_aws_auth(self):
        filename = f"{command_dir}/http2har/awsauth.http"
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hai")
            f.flush()
            result = self.execute_payload(
                target='1', file=filename, fileinputarg=f.name).result
            self.assertEqual("GET", result['target']['1']['method'], )
            self.assertEqual("https://s3.amazonaws.com",
                             result['target']['1']['url'], )
            for headerData in result['target']['1']['headers']:
                name = headerData['name']
                self.assertTrue(name.startswith('x-amz') or name.lower().startswith('authorization'),
                                'header should be x-amz or authorization')
                if headerData['name'].lower() == "authorization":
                    self.assertTrue(
                        "/eu-east-1/s3/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=" in
                        headerData['value'])

                # def test_digestauth(self):

    #     filename = f"{command_dir}/payload.http"
    #     self.assertEqual({'target': {'basicauth': {'headers': [{'name': 'Authorization',
    #                                                             'value': 'Basic '
    #                                                                      'dXNlcm5hbWU6cGFzc3dvcmQ='}],
    #                                                'method': 'GET',
    #                                                'payload': {},
    #                                                'query': [],
    #                                                'url': 'https://req.dothttp.dev'}}},
    #                      self.execute_payload(target='digestauth', file=filename).result)

    def execute_payload(self, fileinputarg="", **kwargs):
        kwargs["properties"] = {"filename":
                                os.path.join(
                                    dir_path, f"{command_dir}/payload.http"),
                                "fileinput2": fileinputarg}
        command = Command(
            method=Http2Har.name,
            params=kwargs,
            id=1)
        result = self.execute_handler.run(command=command)
        # eprint("{\"" + "request" + "\":", json.dumps(result.result['target'][kwargs['target']]), "},")
        self.assertFalse(result.result.get("error", False))
        return result

    def test_context(self):
        command = Command(
            method=Http2Har.name,
            params={
                "contexts": [
                    """
// {{some_variable=some_value}}
@name("base")
GET "https://req.dothttp.dev/some/path"
"""],
                "content":
                """
@name("some request"): "base"
GET '/{{some_variable}}'
""",
                "file": None,
                "target": "1",
                "properties": {
                }
            },
            id=1)
        result = self.execute_handler.run(command=command)
        self.assertFalse(result.result.get("error", False))
        self.assertEqual({'target': {'1': {'headers': [],
                                           'method': 'GET',
                                           'payload': {},
                                           'query': [],
                                           'url': 'https://req.dothttp.dev/some/path/some_value'}}}, result.result)
