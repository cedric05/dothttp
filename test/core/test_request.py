import os
import sys
import tempfile
import unittest

from dothttp.exceptions import *
from dothttp.request_base import CurlCompiler, HttpFileFormatter
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

    # remove default method
    # def test_default_get(self):
    #     req = self.get_request(f"{base_dir}/defaultget.http")
    #     self.assertEqual("GET", req.method)

    def test_headers(self):
        req = self.get_request(f"{base_dir}/defaultget.http")
        self.assertEqual({"headerkey": "headervalue"}, req.headers)

    def test_fail(self):
        with self.assertRaises(HttpFileException):
            req = self.get_request(f"{base_dir}/fail.http")

    def test_fail2(self):
        with self.assertRaises(HttpFileException):
            req = self.get_request(f"{base_dir}/fail2.http")

    @unittest.skipUnless(sys.platform.startswith("linux"), "requires linux")
    def test_output(self):
        with tempfile.NamedTemporaryFile() as f:
            req = self.get_req_comp(f"{base_dir}/output.http",
                                    properties=[f"file={f.name}"])
            req.run()
            data = f.read()
            self.assertIn(
                b'curl -X GET "https://req.dothttp.dev/" \\\n    -H "connection: Keep-Alive" \\\n    -H ',
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
        self.assertEqual("""curl -X GET --url http://endeavour.today/ \\
""", output)

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

    def test_curl_query(self):
        req = self.get_req_comp(f"{sub_dir}/query.http", stdout=True, curl=True)
        self.assertEqual("""curl -X POST --url https://dothttp.azurewebsites.net/ram?key1=value1&key2=value2 \\
-H 'content-type: application/json' \\
-d '{
    "key1": "value2"
}'""", req.get_curl_output())

    def test_curl_query2(self):
        req = self.get_req_comp(f"{base_dir}/query.http", stdout=True, curl=True)
        self.assertEqual("""curl -X GET --url https://dothttp.azurewebsites.net/?key3=value3&key1=value1&key2=value2 \\
""", req.get_curl_output())

    def test_quoted3_format_print(self):
        req = self.get_req_comp(f"{sub_dir}/quoted.http", format=True, stdout=True)
        req.load()
        output = req.format(req.model)
        self.assertEqual("""POST "https://{{host1}}/ram"
? "{{queryname1}}"= "value1"
? "key2"= "{{valuename1}}"
data('
"hi this is good"
\\'this barbarian\\'
')
output(test)


""", output)

    @unittest.skipUnless(sys.platform.startswith("win"), "requires Windows")
    def test_multiline_curl(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # with files
            self.assertEqual(f'''curl -X POST --url https://httpbin.org/post \\
--form 'test=@{f.name}' \\
--form hi=hi2''', self.get_curl_out(f))

            # with file input
            self.assertEqual(f"""curl -X POST --url https://httpbin.org/post \\
--data '@{f.name}'""", self.get_curl_out(f, 2))

            # with json out
            self.assertEqual("""curl -X POST --url https://httpbin.org/post \\
-H 'content-type: application/json' \\
-d '{
    "hi": "hi2"
}'""", self.get_curl_out(f, 3))

    @unittest.skipUnless(sys.platform.startswith("linux"), "requires linux")
    def test_multiline_curl_linux(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # with files
            self.assertEqual(f'''curl -X POST --url https://httpbin.org/post \\
--form test=@{f.name} \\
--form hi=hi2''', self.get_curl_out(f))

            # with file input
            self.assertEqual(f'''curl -X POST --url https://httpbin.org/post \\
--data @{f.name}''', self.get_curl_out(f, 2))

            # with json out
            self.assertEqual("""curl -X POST --url https://httpbin.org/post \\
-H 'content-type: application/json' \\
-d '{
    "hi": "hi2"
}'""", self.get_curl_out(f, 3))

            self.assertEqual("""curl -X POST --url https://httpbin.org/post \\
-H 'content-type: text/xml' \\
-d '<xml>
    <body> hi this is test body</body>
</xml>
'""", self.get_curl_out(f, 4))

    def test_awsauth_linux(self):
        comp2 = self.get_req_comp(f'{base_dir}/awsauth.http', curl=True,
                                  target='1')
        curl_out = comp2.get_curl_output()
        #         self.assertEqual("curl -X GET --url http://s3.amazonaws.com/ \
        # -H 'x-amz-date: 20210815T170418Z' \
        # -H 'x-amz-content-sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855' \
        # -H 'Authorization: AWS4-HMAC-SHA256 Credential=dummy/20210815/us-east-1/s3/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=9fef2c230112a434be3b38d6979b95db71b58fbe60e3e20cbf70116c07f8eaa5'", curl_out)
        self.assertTrue("curl -X GET --url http://s3.amazonaws.com/" in curl_out)
        self.assertTrue("-H 'x-amz-date:" in curl_out)
        self.assertTrue("-H 'x-amz-content-sha256:" in curl_out)
        self.assertTrue("-H 'Authorization: AWS4-HMAC-SHA256 Credential=dummy/" in curl_out)
        self.assertTrue(
            "/us-east-1/s3/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=" in curl_out)

    def get_curl_out(self, f, target=1):
        comp2 = self.get_req_comp(f'{base_dir}/curlgen.http', curl=True, properties=[f"filename={f.name}"],
                                  target=target)
        out2 = comp2.get_curl_output()
        return out2

    @unittest.skipUnless(sys.platform.startswith("linux"), "requires linux")
    def test_curl_urlencoded_payload(self):
        comp2 = self.get_req_comp(f'{base_dir}/curlgen.http', curl=True,
                                  target="urlencoded")
        out = comp2.get_curl_output()
        self.assertEqual("""curl -X POST --url https://httpbin.org/post \\
-H 'content-type: application/x-www-form-urlencoded' \\
-d 'test=hai&test=bye&test2=ram'""", out)

    def test_aws_format_check(self):
        # awsauth is used for unit test cases
        # and for format check
        # changing here or there makes test fails
        # going forward, seperate files will have to be used
        comp2: HttpFileFormatter = self.get_req_comp(f'{base_dir}/awsauth.http', curl=True,
                                                     target='1', format=True)
        with open(f"{base_dir}/awsauth_format.http") as f:
            self.assertEqual(f.read(), comp2.format(comp2.model))

    def test_p12_certificate_format(self):
        comp2: HttpFileFormatter = self.get_req_comp(f'{base_dir}/../root_cert/http/no-password.http', curl=True,
                                                     target='1', format=True)
        with open(f"{base_dir}/no-password_format.http") as f:
            self.assertEqual(f.read(), comp2.format(comp2.model))

    def test_aws_auth_curl_output_with_post_data_and_content_type(self):
        """
            This use-case works for both curl with content-type defined in http
            and, aws auth with post data working one
        Returns:

        """
        comp2: CurlCompiler = self.get_req_comp(f'{base_dir}/awsauth.http', curl=True,
                                                target='with-x-amz-date header with post data')
        self.assertEqual("""curl -X POST --url https://api.ecr.us-east-1.amazonaws.com/ \\
-H 'x-amz-date: 20210817T103121Z' \\
-H 'x-amz-content-sha256: 44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a' \\
-H 'Authorization: AWS4-HMAC-SHA256 Credential=dummy/20210817/us-east-1/ecr/aws4_request, SignedHeaders=content-type;host;x-amz-content-sha256;x-amz-date;x-amz-target, Signature=1d236ae264049a0b7e6c8374d053d824f6f5ccf6b183677d15791b3b98f663ee' \\
-H 'Content-Type: application/x-amz-json-1.1' \\
-H 'X-Amz-Target: AmazonEC2ContainerRegistry_V20150921.DescribeRegistry' \\
-H 'x-amz-date: 20210817T103121Z' \\
-d '{}'""", comp2.get_curl_output())

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
