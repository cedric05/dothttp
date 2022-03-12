import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from dotextensions.server.handlers.http2postman import Http2Postman
from dotextensions.server.models import Command
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
command_dir = Path(f"{dir_path}/commands")
http2postman_dir = Path(f"{command_dir}/http2postman")
requests_dir = Path(f"{dir_path}/../core/requests")


class Testhttp2postman(TestBase):
    def setUp(self) -> None:
        self.execute_handler = Http2Postman()

    def execute_n_get(self, expected_output, input_file):
        self.maxDiff = None
        with tempfile.TemporaryDirectory() as f:
            with open(os.path.join(command_dir, expected_output)) as f2:
                data = json.load(f2)
            for contentOrFile in [False, True, ]:
                fullpath = input_file
                content = None
                if contentOrFile and os.path.isfile(fullpath):
                    with open(fullpath) as f:
                        content = f.read()
                result = self.execute_handler.run(command=Command(
                    method=self.execute_handler.name,
                    id=92,
                    params={"filename": fullpath, "content": content, "directory": f,
                            "properties": {"filename": input_file}}))
                self.assertDictEqual(data, result.result)
            # with open(os.path.join(command_dir, expected_output), 'w') as f2:
            #     json.dump(result.result, f2, indent=True)

    def test_simple(self):
        self.execute_n_get(expected_output="export1.postman.json",
                           input_file=os.path.join(command_dir, "swagger2har_petstore_response.http"))

    # current
    # in windows content-type is set to application/bytestream
    @unittest.skipUnless(sys.platform.startswith("linux"), "requires linux")
    def test_payload(self):
        """
        This test case consists of various payload formats
         1. payload with data
         2. payload with json
         3. payload with urlencoded
         4. payload with form
         5. payload with binary
        """
        self.execute_n_get("payload.postman_collection.json", os.path.join(command_dir, "payload.http"))

    def test_url_query(self):
        """
            Below collection should consist of these variations
             1. query with url
             2. headers with url
             3. query in url and externally defined
             4. auth
             5. ~~certificate~~
        """
        self.execute_n_get("urlquery.postman_collection.json", os.path.join(command_dir, "urlquery.http"))

    def error_scenario(self, input_file):
        self.maxDiff = None
        with tempfile.TemporaryDirectory() as f:
            fullpath = os.path.join(command_dir, input_file)
            content = None
            result = self.execute_handler.run(command=Command(
                method=self.execute_handler.name,
                id=92,
                params={"filename": fullpath, "content": content, "directory": f}))
            return result.result

    def test_negative(self):
        self.assertEquals({'error': True, 'error_message': 'filename not existent or invalid link'},
                          self.error_scenario("ram.http"))
        second = self.error_scenario("names_fail.http")
        self.assertTrue(second.get("error"))
        self.assertTrue(second.get("error_message").startswith(
            "unable to parse because of parsing issues None:2:2: error: Expected '(' or STRING or '\w+' at position"))

    def test_extend(self):
        self.execute_n_get("auth_extend.postman_collection.json", os.path.join(requests_dir, "auth_extend.http"))

    def test_url_with_port(self):
        self.execute_n_get("url_query.postman_collection.json", os.path.join(command_dir, "urlquerywithport.http"))

    def test_unparseble_port(self):
        self.execute_n_get(http2postman_dir.joinpath("test_unparseble_port.postman_collection.json"),
                           os.path.join(http2postman_dir, "test_unparseble_port.http"))

    def test_aws_auth(self):
        self.execute_n_get(http2postman_dir.joinpath("awsauth.postman_collection.json"),
                           os.path.join(http2postman_dir, "awsauth.http"))

    def test_export_varibles(self):
        self.execute_n_get(
            http2postman_dir.joinpath("withenv", "exportdothttpenv.postman_collection.json"),
            str(http2postman_dir.joinpath("withenv", "exportdothttpenv.http")),
        )

    def test_folder(self):
        self.execute_n_get(
            http2postman_dir.joinpath("folderupload", "examples.postman_collection.json"),
            str(http2postman_dir.joinpath("folderupload", "examples")),
        )

    def test_ntlm_auth(self):
        self.execute_n_get(http2postman_dir.joinpath("ntlmauth.postman_collection.json"),
                           os.path.join(http2postman_dir, "ntlm_auth.http"))
