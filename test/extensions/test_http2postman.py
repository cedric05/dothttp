import json
import os
import tempfile
from pathlib import Path

from dotextensions.server.handlers.http2postman import Http2Postman
from dotextensions.server.models import Command
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
command_dir = Path(f"{dir_path}/commands")


class Testhttp2postman(TestBase):
    def setUp(self) -> None:
        self.execute_handler = Http2Postman()

    def execute_n_get(self, expected_output, input_file):
        self.maxDiff = None
        with tempfile.TemporaryDirectory() as f:
            with open(os.path.join(command_dir, expected_output)) as f2:
                data = json.load(f2)
            for contentOrFile in [True, False]:
                fullpath = os.path.join(command_dir, input_file)
                content = None
                if contentOrFile:
                    with open(fullpath) as f:
                        content = f.read()
                result = self.execute_handler.run(command=Command(
                    method=self.execute_handler.name,
                    id=92,
                    params={"filename": fullpath, "content": content, "directory": f}))
                self.assertEqual(data, result.result)

    def test_simple(self):
        self.execute_n_get(expected_output="export1.postman.json", input_file="swagger2har_petstore_response.http")

    def test_payload(self):
        """
        This test case consists of various payload formats
         1. payload with data
         2. payload with json
         3. payload with urlencoded
         4. payload with form
         5. payload with binary
        """
        self.execute_n_get("payload.postman_collection.json", "payload.http")

    def test_url_query(self):
        """
            Below collection should consist of these variations
             1. query with url
             2. headers with url
             3. query in url and externally defined
             4. auth
             5. ~~certificate~~
        """
        self.execute_n_get("urlquery.postman_collection.json", "urlquery.http")

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
