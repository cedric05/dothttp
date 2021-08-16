import json
import os
import unittest

from dotextensions.server.handlers.basic_handlers import RunHttpFileHandler, GetNameReferencesHandler, \
    ContentNameReferencesHandler
from dotextensions.server.models import Command
from test import TestBase
from test.core.test_certs import http_base, cert_base

dir_path = os.path.dirname(os.path.realpath(__file__))
command_dir = f"{dir_path}/commands"


class TargetTest(TestBase):

    def setUp(self) -> None:
        self.name_handler = GetNameReferencesHandler()

    def test_names(self):
        result = self.name_handler.run(Command(
            method=GetNameReferencesHandler.name,
            params={"file": f"{command_dir}/names.http"},
            id=1
        ))
        return self.execute_and_compare_names(result)

    def execute_and_compare_names(self, result):
        self.assertEqual({'names': [{'end': 77, 'method': 'GET', 'name': 'test', 'start': 0},
                                    {'end': 207, 'method': 'POST', 'name': 'test2', 'start': 79},
                                    {'end': 337, 'method': 'POST', 'name': 'test3', 'start': 209},
                                    {'end': 398, 'method': 'POST', 'name': 'test4.test', 'start': 339}],
                          'urls': [{'end': 41,
                                    'method': 'GET',
                                    'start': 14,
                                    'url': 'https://req.dothttp.dev'},
                                   {'end': 120,
                                    'method': 'POST',
                                    'start': 92,
                                    'url': 'https://req.dothttp.dev'},
                                   {'end': 250,
                                    'method': 'POST',
                                    'start': 222,
                                    'url': 'https://req.dothttp.dev'},
                                   {'end': 387,
                                    'method': 'POST',
                                    'start': 359,
                                    'url': 'https://req.dothttp.dev'}]},
                         result.result)

    def test_content_names2(self):
        filename = f"{command_dir}/names.http"
        with open(filename) as f:
            result = ContentNameReferencesHandler().run(Command(
                method=ContentNameReferencesHandler.name,
                params={"content": f.read()},
                id=1
            ))
            return self.execute_and_compare_names(result)

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


class FileExecute(TestBase):
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
        self.assertEqual('''@name("2")
POST "https://httpbin.org/post"
? "startusing"= "dothttp"



''', result.result['http'])

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
        self.assertEqual("""@name("2")
POST "https://req.dothttp.dev/post"
? "startusing"= "dothttp"



""", result2.result['http'])

        result3 = self.execute_handler.run(Command(
            method=RunHttpFileHandler.name,
            params={
                "file": f"{command_dir}/complexrun.http",
                "target": "3",
                "properties": {
                    "host": "httpbin.org"
                }
            },
            id=1)
        )
        self.assertEqual("""@name("3")
POST "https://httpbin.org/POST"
? "startusing"= "dothttp"



""", result3.result['http'])
        self.assertEqual(404, result3.result["status"])

        result4 = self.execute_handler.run(Command(
            method=RunHttpFileHandler.name,
            params={
                "file": f"{command_dir}/complexrun.http",
                "target": "4",
                "properties": {
                    "host": "httpbin.org"
                }
            },
            id=1)
        )
        self.assertEqual(200, result4.result["status"])
        self.assertEqual("""@name("4")
GET "https://httpbin.org/get"
basicauth("username", "password")



""", result4.result['http'])

    def test_non_existant_file(self):
        result = self.execute_file(f"{command_dir}/syntax2.http")
        self.assertEqual(True, result.result['error'])

    def test_syntax_issue_file(self):
        result = self.execute_file(f"{command_dir}/syntax.http")
        self.assertEqual(True, result.result['error'])

    def execute_file(self, filename, env=None, properties=None, target=None):
        if properties is None:
            properties = {}
        if env is None:
            env = []
        params = {
            "file": filename,
            "env": env,
            "properties": properties
        }
        if target:
            params['target'] = target
        result = self.execute_handler.run(Command(
            method=RunHttpFileHandler.name,
            params=params,
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

    def test_cert_with_no_key(self):
        filename = f"{http_base}/no-password.http"
        cert_file = f"{cert_base}/no-password.pem"
        req_comp_success = self.execute_file(filename, target="no-password", properties={"cert": cert_file, "file": ""})
        self.assertEqual(200, req_comp_success.result['status'])
        self.assertEqual("""@name("no-password")
GET "https://client.badssl.com/"
certificate(cert="value")



""", req_comp_success.result['http'])

    def test_cert_key(self):
        filename = f"{http_base}/no-password.http"
        cert_file = f"{cert_base}/cert.crt"
        key_file = f"{cert_base}/key.key"
        req_comp2 = self.execute_file(filename, target="with-key-and-cert",
                                      properties={"cert": cert_file, "key": key_file})
        self.assertEqual(200, req_comp2.result['status'])
        self.assertEqual("""@name("with-key-and-cert")
@clear
@insecure
GET "https://client.badssl.com/"
certificate(cert="value", key="value")



""", req_comp2.result['http'])

    def test_p12(self):
        filename = f"{http_base}/no-password.http"
        p12 = f"{cert_base}/badssl.com-client.p12"
        result = self.execute_file(filename, properties={"p12": p12, "password": "badssl.com"}, target="with-p12")
        self.assertEqual(200, result.result['status'])
        self.assertEqual("""@name("with-p12")
@clear
GET "https://client.badssl.com/"
p12(file="value", password="value")



""", result.result["http"])

    def test_awsauth(self):
        result = self.execute_file(f"{command_dir}/http2har/awsauth.http")
        # this is expected
        # as we don't have valid access_id and valid secret_key
        self.assertEqual(400, result.result['status'])
        self.assertEqual("""@name("1")
GET "https://s3.amazonaws.com"
awsauth(access_id="dummy", secret_key="dummy", service="s3", region="eu-east-1")



""", result.result['http'])


if __name__ == '__main__':
    unittest.main()
