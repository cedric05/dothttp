import os
import tempfile
import unittest

from dothttp import HttpFileException
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
base_dir = f"{dir_path}/requests"
sub_dir = f"{dir_path}/substitution"


class RequestTest(TestBase):
    def test_get(self):
        req = self.get_request(f"{base_dir}/pass.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url, "incorrect url")
        self.assertEqual("GET", req.method, "incorrect url")

    def test_post(self):
        req = self.get_request(f"{base_dir}/pass2.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url, "incorrect url")
        self.assertEqual("POST", req.method, "incorrect url")

    def test_query(self):
        req = self.get_request(f"{base_dir}/query.http")
        self.assertEqual("https://dothttp.azurewebsites.net/?key3=value3&key1=value1&key2=value2", req.url,
                         "incorrect url computed")
        self.assertEqual("GET", req.method, "incorrect method")

    def test_file_notfound(self):
        pass

    def test_syntax_problem(self):
        pass

    def test_default_get(self):
        req = self.get_request(f"{base_dir}/defaultget.http")
        self.assertEqual("GET", req.method)

    def test_headers(self):
        req = self.get_request(f"{base_dir}/defaultget.http")
        self.assertEqual({"headerkey": "headervalue"}, req.headers)

    def test_fail(self):
        with self.assertRaises(HttpFileException):
            req = self.get_request(f"{base_dir}/fail.http")

    def test_output(self):
        with tempfile.NamedTemporaryFile() as f:
            req = self.get_req_comp(f"{base_dir}/output.http",
                                    properties=[f"file={f.name}"])
            req.run()
            data = f.read()
            self.assertIn(
                b'curl "https://dothttp.azurewebsites.net/" \\\n    -X GET \\\n    -H "connection: Keep-Alive" \\\n    -H ',
                data
            )

    def test_non200(self):
        req = self.get_req_comp(f"{base_dir}/non200.http", info=True)
        req.run()

    def test_redirect(self):
        req = self.get_req_comp(f"{base_dir}/redirect.http", info=True)
        req.run()

    def test_curl_print(self):
        ## TODO check curl output
        req = self.get_req_comp(f"{base_dir}/redirect.http", info=True, curl=True)
        req.run()

    def test_format_print(self):
        ## TODO check history
        ## actually
        req = self.get_req_comp(f"{base_dir}/redirect.http", format=True, stdout=True)
        req.run()

    def test_format2_print(self):
        ## move to seperate folder for integration
        ## test formatted output
        req = self.get_req_comp(f"{sub_dir}/multipleenv.http", format=True, stdout=True)
        req.run()


if __name__ == "__main__":
    unittest.main()
