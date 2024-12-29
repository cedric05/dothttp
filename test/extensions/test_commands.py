import json
import os
import unittest
from test import TestBase
from test.core.test_certs import cert_base, http_base
from unittest import skip

from dotextensions.server.handlers.basic_handlers import (
    ContentNameReferencesHandler,
    GetNameReferencesHandler,
    RunHttpFileHandler,
)
from dotextensions.server.models import Command
from dothttp.parse.request_base import DOTHTTP_COOKIEJAR, RequestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
command_dir = f"{dir_path}/commands"


class TargetTest(TestBase):
    def setUp(self) -> None:
        self.maxDiff = None
        self.name_handler = GetNameReferencesHandler()

    def test_names(self):
        result = self.name_handler.run(
            Command(
                method=GetNameReferencesHandler.name,
                params={"file": f"{command_dir}/names.http"},
                id=1,
            )
        )
        return self.execute_and_compare_names(result)

    def execute_and_compare_names(self, result):
        self.assertEqual(
            {
                "names": [
                    {"end": 77, "method": "GET", "name": "test", "start": 0},
                    {"end": 207, "method": "POST", "name": "test2", "start": 79},
                    {"end": 337, "method": "POST", "name": "test3", "start": 209},
                    {"end": 398, "method": "POST", "name": "test4.test", "start": 339},
                ],
                "urls": [
                    {
                        "end": 41,
                        "method": "GET",
                        "start": 14,
                        "url": "https://req.dothttp.dev",
                    },
                    {
                        "end": 120,
                        "method": "POST",
                        "start": 92,
                        "url": "https://req.dothttp.dev",
                    },
                    {
                        "end": 250,
                        "method": "POST",
                        "start": 222,
                        "url": "https://req.dothttp.dev",
                    },
                    {
                        "end": 387,
                        "method": "POST",
                        "start": 359,
                        "url": "https://req.dothttp.dev",
                    },
                ],
                "imports": {"names": [], "urls": []},
            },
            result.result,
        )

    def test_content_names2(self):
        filename = f"{command_dir}/names.http"
        with open(filename) as f:
            result = ContentNameReferencesHandler().run(
                Command(
                    method=ContentNameReferencesHandler.name,
                    params={"content": f.read()},
                    id=1,
                )
            )
            return self.execute_and_compare_names(result)

    def test_notexistant_file(self):
        result = self.name_handler.run(
            Command(
                method=GetNameReferencesHandler.name,
                params={"file": f"{command_dir}/names2.http"},
                id=1,
            )
        )
        self.assertTrue(result.result["error"])

    def test_syntax_error_name(self):
        result = self.name_handler.run(
            Command(
                method=GetNameReferencesHandler.name,
                params={"file": f"{command_dir}/names_fail.http"},
                id=1,
            )
        )
        self.assertTrue(result.result["error"])


class FileExecute(TestBase):
    def setUp(self) -> None:
        self.execute_handler = RunHttpFileHandler()

    def test_execute_file(self):
        result = self.execute_handler.run(
            Command(
                method=RunHttpFileHandler.name,
                params={"file": f"{command_dir}/simple.http"},
                id=1,
            )
        )
        body = json.loads(result.result["body"])
        self.assertTrue("args" in body)
        self.assertTrue("headers" in body)
        self.assertEqual({}, body["args"])
        self.assertEqual("http://localhost:8000/get", body["url"])

    def test_complex_file(self):
        result = self.execute_handler.run(
            Command(
                method=RunHttpFileHandler.name,
                params={"file": f"{command_dir}/complexrun.http", "target": "2"},
                id=1,
            )
        )
        body = json.loads(result.result["body"])
        self.assertTrue("status" in result.result)
        self.assertEqual(200, result.result["status"])
        self.assertTrue("headers" in result.result)
        self.assertEqual("http://localhost:8000/post?startusing=dothttp", body["url"])
        self.assertEqual(
            """var host = 'localhost:8000' ;
@name("2")
POST "http://localhost:8000/post"
? "startusing"= "dothttp"



""",
            result.result["http"],
        )

        result2 = self.execute_handler.run(
            Command(
                method=RunHttpFileHandler.name,
                params={
                    "file": f"{command_dir}/complexrun.http",
                    "target": "2",
                    "properties": {"host": "req.dothttp.dev"},
                },
                id=1,
            )
        )
        self.assertTrue("status" in result2.result)
        self.assertEqual(200, result2.result["status"])
        self.assertTrue("headers" in result2.result)
        self.assertEqual("http://localhost:8000/post?startusing=dothttp", body["url"])
        self.assertEqual(
            """var host = 'req.dothttp.dev' ;
@name("2")
POST "http://req.dothttp.dev/post"
? "startusing"= "dothttp"



""",
            result2.result["http"],
        )

        result3 = self.execute_handler.run(
            Command(
                method=RunHttpFileHandler.name,
                params={
                    "file": f"{command_dir}/complexrun.http",
                    "target": "3",
                    "properties": {"host": "localhost:8000"},
                },
                id=1,
            )
        )
        self.assertEqual(
            """var host = 'localhost:8000' ;
@name("3")
POST "http://localhost:8000/POST"
? "startusing"= "dothttp"



""",
            result3.result["http"],
        )
        self.assertEqual(404, result3.result["status"])

        result4 = self.execute_handler.run(
            Command(
                method=RunHttpFileHandler.name,
                params={
                    "file": f"{command_dir}/complexrun.http",
                    "target": "4",
                    "properties": {"host": "localhost:8000"},
                },
                id=1,
            )
        )
        self.assertEqual(200, result4.result["status"])
        self.assertEqual(
            """var host = 'localhost:8000' ;
@name("4")
GET "http://localhost:8000/get"
basicauth("username", "password")



""",
            result4.result["http"],
        )

    def test_non_existant_file(self):
        result = self.execute_file(f"{command_dir}/syntax2.http")
        self.assertEqual(True, result.result["error"])

    def test_syntax_issue_file(self):
        result = self.execute_file(f"{command_dir}/syntax.http")
        self.assertEqual(True, result.result["error"])

    def execute_file(
        self, filename, env=None, properties=None, target=None, property_file=None
    ):
        if properties is None:
            properties = {}
        if env is None:
            env = []
        params = {
            "file": filename,
            "env": env,
            "properties": properties,
            "property-file": property_file,
        }
        if target:
            params["target"] = target
        result = self.execute_handler.run(
            Command(method=RunHttpFileHandler.name, params=params, id=1)
        )
        return result

    def test_property_not_found(self):
        result = self.execute_file(f"{command_dir}/env.http")
        self.assertEqual(True, result.result["error"])

    def test_env(self):
        result = self.execute_file(f"{command_dir}/isolated/env.http", env=["simple"])
        self.assertEqual(200, result.result["status"])

    def test_execute(self):
        result = self.execute_file(f"{command_dir}/cookie.http", target="set-cookie")
        self.assertEqual(
            """@name("set-cookie")
GET "http://localhost:8000/cookies/set/dev/ram"
"cookie": "dev=ram"



""",
            result.result["http"],
        )
        os.remove(DOTHTTP_COOKIEJAR)
        RequestBase.global_session.cookies.clear()

    def test_property(self):
        result = self.execute_file(
            f"{command_dir}/isolated/env.http", properties={"path": "get"}
        )
        self.assertEqual(200, result.result["status"])

    @skip("""
    can be skipped as path may vary
    """)
    def test_cert_with_no_key(self):
        filename = f"{http_base}/no-password.http"
        cert_file = f"{cert_base}/no-password.pem"
        req_comp_success = self.execute_file(
            filename, target="no-password", properties={"cert": cert_file, "file": ""}
        )
        self.assertEqual(200, req_comp_success.result["status"])
        self.assertEqual(
            f"""var cert = '/home/runner/work/dothttp/dothttp/test/core/root_cert/certs/no-password.pem' ;
var key ;
var p12 ;
var file = '' ;
@name("no-password")
GET "https://client.badssl.com/"
certificate(cert="{cert_file}")



""",
            req_comp_success.result["http"],
        )

    @skip("""
    can be skipped as path may vary
    """)
    def test_cert_key(self):
        filename = f"{http_base}/no-password.http"
        cert_file = f"{cert_base}/cert.crt"
        key_file = f"{cert_base}/key.key"
        req_comp2 = self.execute_file(
            filename,
            target="with-key-and-cert",
            properties={"cert": cert_file, "key": key_file},
        )
        self.assertEqual(200, req_comp2.result["status"])
        self.assertEqual(
            f"""var cert = '/home/runner/work/dothttp/dothttp/test/core/root_cert/certs/cert.crt' ;
var key = '/home/runner/work/dothttp/dothttp/test/core/root_cert/certs/key.key' ;
var p12 ;
@name("with-key-and-cert")
@clear
@insecure
GET "https://client.badssl.com/"
certificate(cert="{cert_file}", key="{key_file}")



""",
            req_comp2.result["http"],
        )

    @skip("""
    can be skipped as path may vary
    """)
    def test_p12(self):
        filename = f"{http_base}/no-password.http"
        p12 = f"{cert_base}/badssl.com-client.p12"
        result = self.execute_file(
            filename,
            properties={"p12": p12, "password": "badssl.com"},
            target="with-p12",
        )
        self.assertEqual(200, result.result["status"])
        self.assertEqual(
            f"""var cert ;
var key ;
var p12 = '/home/runner/work/dothttp/dothttp/test/core/root_cert/certs/badssl.com-client.p12' ;
var password = 'badssl.com' ;
@name("with-p12")
@clear
GET "https://client.badssl.com/"
p12(file="{p12}", password="badssl.com")



""",
            result.result["http"],
        )

    def test_awsauth(self):
        result = self.execute_file(f"{command_dir}/http2har/awsauth.http")
        # this is expected
        # as we don't have valid access_id and valid secret_key
        self.assertEqual(400, result.result["status"])
        self.assertEqual(
            """@name("1")
GET "https://s3.amazonaws.com"
awsauth(access_id="dummy", secret_key="dummy", service="s3", region="eu-east-1")



""",
            result.result["http"],
        )

    def test_property_file(self):
        http_file = f"{command_dir}/custom-property/property.http"
        result = self.execute_file(
            http_file,
            property_file=os.path.join(
                os.path.dirname(http_file), "different-name.json"
            ),
            env=["env"],
        )
        self.assertEqual(200, result.result["status"])
        body = json.loads(result.result["body"])
        self.assertEqual({"prop": "value"}, body["json"])
        print(result)


    def test_property_sub(self):
        http_file = f"{command_dir}/custom-property/property-refer.http"
        result = self.execute_file(
            http_file,
        )
        self.assertEqual(200, result.result["status"])
        body = json.loads(result.result["body"])
        self.assertEqual({'fullName': 'John Doe'}, body["json"])
        print(result)

    def test_property_sub(self):
        http_file = f"{command_dir}/custom-property/property-refer.http"
        result = self.execute_file(
            http_file,
            properties={
                "prefix": "Mr."
            },
        )
        self.assertEqual(200, result.result["status"])
        body = json.loads(result.result["body"])
        self.assertEqual({'fullName': 'John Doe'}, body["json"])

    def test_property_sub_from_command_line_props(self):
        http_file = f"{command_dir}/custom-property/property-refer.http"
        result = self.execute_file(
            http_file,
            properties={
                "prefix": "Mr."
            },
            target='env-property-refer'
        )
        self.assertEqual(200, result.result["status"])
        body = json.loads(result.result["body"])
        self.assertEqual({'fullName': 'Mr. John Doe'}, body["json"])



if __name__ == "__main__":
    unittest.main()
