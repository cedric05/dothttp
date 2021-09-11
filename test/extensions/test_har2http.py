import contextlib
import json
import os
import tempfile

from dotextensions.server.handlers.har2httphandler import Har2HttpHandler
from dotextensions.server.models import Command
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
command_dir = f"{dir_path}/commands"

handler = Har2HttpHandler()


@contextlib.contextmanager
def execute_with_params(input_file_or_json, expected_output):
    if isinstance(input_file_or_json, (dict, list)):
        full_path = None
        har_data = input_file_or_json
    else:
        full_path = os.path.join(command_dir, input_file_or_json)
        har_data = None
    with tempfile.TemporaryDirectory() as directory:
        command = Command(id=1, method=Har2HttpHandler.name, params={"filename": full_path,
                                                                     "save_directory": directory,
                                                                     "har": har_data})
        response = handler.run(command)
        with open(os.path.join(command_dir, expected_output
                               ), 'r') as f:
            yield f.read(), response


class Har2HttpTest(TestBase):

    def test_simple(self):
        with execute_with_params(input_file_or_json="swagger2har_petstore_response.json",
                                 expected_output="swagger2har_petstore_response.http") as (expected, response):
            self.assertEqual(expected, response.result.get('http'))

    def test_simple2(self):
        with execute_with_params(input_file_or_json="req.har.json", expected_output="req.har.http") as (
                expected, response):
            self.assertEqual(expected, response.result.get('http'))

    def test_har_list(self):
        with open(os.path.join(command_dir, "req.har.json")) as f:
            har_data = json.load(f)
        har_requests = [entry['request'] for entry in har_data['log']['entries']]
        with execute_with_params(input_file_or_json=har_requests, expected_output="req.har.http") as (
                expected, response):
            self.assertEqual(expected, response.result.get('http'))

    def test_har_simple3(self):
        with execute_with_params(input_file_or_json="payload.har.json",
                                 expected_output="payload.from.har.http") as (expected, response):
            self.assertEqual(expected, response.result.get('http'))

    def test_should_error_out(self):
        with execute_with_params("ram", expected_output="req.har.http") as (expected, response):
            self.assertTrue(response.result.get('error'))

    def test_should_error_out2(self):
        with execute_with_params("2", expected_output="req.har.http") as (expected, response):
            self.assertTrue(response.result.get('error'))

    def test_should_import(self):
        with execute_with_params("harwithquotes.json", "harwithquotesimport.http") as (expected, response):
            self.assertEqual(expected, response.result.get('http'))

    def test_har_2_http_with_json(self):
        with execute_with_params(os.path.join("har2http", "postjsontypenotjson.json"),
                                 os.path.join("har2http", "postjsontypenotjson.http")) as (expected, response):
            self.assertEqual(expected, response.result.get('http'))
