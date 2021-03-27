import os
import sys
import tempfile
import unittest

from dothttp.exceptions import *
from dothttp.request_base import CurlCompiler
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

    def test_default_get(self):
        req = self.get_request(f"{base_dir}/defaultget.http")
        self.assertEqual("GET", req.method)

    def test_headers(self):
        req = self.get_request(f"{base_dir}/defaultget.http")
        self.assertEqual({"headerkey": "headervalue"}, req.headers)

    def test_fail(self):
        with self.assertRaises(HttpFileException):
            req = self.get_request(f"{base_dir}/fail.http")

    def test_fail2(self):
        with self.assertRaises(HttpFileException):
            req = self.get_request(f"{base_dir}/fail2.http")

    def test_output(self):
        with tempfile.NamedTemporaryFile() as f:
            req = self.get_req_comp(f"{base_dir}/output.http",
                                    properties=[f"file={f.name}"])
            req.run()
            data = f.read()
            self.assertIn(
                b'curl "https://req.dothttp.dev/" \\\n    -X GET \\\n    -H "connection: Keep-Alive" \\\n    -H ',
                data
            )

    def test_non200(self):
        req = self.get_req_comp(f"{base_dir}/non200.http", info=True)
        req.run()

    def test_redirect(self):
        req = self.get_req_comp(f"{base_dir}/redirect.http", info=True)
        req.run()

    def test_curl_print(self):
        req: CurlCompiler = self.get_req_comp(f"{base_dir}/redirect.http", info=True, curl=True)
        output = req.get_curl_output()
        self.assertEqual("""curl -X GET \\
http://endeavour.today/""", output)

    def test_format_print(self):
        req = self.get_req_comp(f"{base_dir}/redirect.http", format=True, stdout=True)
        req.load()
        output = req.format(req.model)
        self.assertEqual('GET "http://endeavour.today/"\n\n\n', output)
        print(output)

    def test_format2_print(self):
        req = self.get_req_comp(f"{sub_dir}/multipleenv.http", format=True, stdout=True)
        req.load()
        output = req.format(req.model)
        self.assertEqual("""POST "https://{{host1}}/ram"
? "{{queryname1}}"= "value1"
? "key2"= "{{valuename1}}"
json({
    "{{queryname2}}": "{{valuename2}}"
})
output(test)


""", output)

    @unittest.skipUnless(sys.platform.startswith("win"), "requires Windows")
    def test_multiline_curl(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # with files
            self.assertEqual(f'''curl -X POST \\
--form 'test=@{f.name}' \\
--form hi=hi2 \\
https://httpbin.org/post''', self.get_curl_out(f))

            # with file input
            self.assertEqual(f'''curl -X POST \\
--data '@{f.name}' \\
https://httpbin.org/post''', self.get_curl_out(f, 2))

            # with json out
            self.assertEqual('''curl -X POST \\
-H 'Content-Length: 13' \\
-H 'Content-Type: application/json' \\
-d '{"hi": "hi2"}' \\
https://httpbin.org/post''', self.get_curl_out(f, 3))

    @unittest.skipUnless(sys.platform.startswith("linux"), "requires linux")
    def test_multiline_curl_linux(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # with files
            self.assertEqual(f'''curl -X POST \\
--form test=@{f.name} \\
--form hi=hi2 \\
https://httpbin.org/post''', self.get_curl_out(f))

            # with file input
            self.assertEqual(f'''curl -X POST \\
--data @{f.name} \\
https://httpbin.org/post''', self.get_curl_out(f, 2))

            # with json out
            self.assertEqual('''curl -X POST \\
-H 'Content-Length: 13' \\
-H 'Content-Type: application/json' \\
-d '{"hi": "hi2"}' \\
https://httpbin.org/post''', self.get_curl_out(f, 3))

    def get_curl_out(self, f, target=1):
        comp2 = self.get_req_comp(f'{base_dir}/curlgen.http', curl=True, properties=[f"filename={f.name}"],
                                  target=target)
        out2 = comp2.get_curl_output()
        return out2

    def test_trailing_commas_are_ok(self):
        filename = f"{base_dir}/trailingcomma.http"
        first_one = self.get_request(filename, target=1)
        second_one = self.get_request(filename, target=2)
        third_one = self.get_request(filename, target=3)
        fourth_one = self.get_request(filename, target=4)

        self.assertEqual("ram=ranga", first_one.body)
        self.assertEqual(b'{"requestseasy": "dothttp", "shouldwork": ["first", "withtrailingcomma"]}', second_one.body)
        self.assertEqual('hi', third_one.body)
        self.assertEqual('https://dev.dothttp.dev/', fourth_one.url)
        self.assertEqual('POST', fourth_one.method)


if __name__ == "__main__":
    unittest.main()
