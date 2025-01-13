import os
import sys
from test import TestBase
from unittest import skip

from dothttp.parse import PropertyNotFoundException
from dothttp.parse.request_base import CurlCompiler

dir_path = os.path.dirname(os.path.realpath(__file__))
cert_base = f"{dir_path}/root_cert/certs"
http_base = f"{dir_path}/root_cert/http"

is_windows = sys.platform.startswith("win")
quote = "'" if is_windows else ""


class CertUnitTest(TestBase):
    def test_fail_no_property_certificate(self):
        with self.assertRaises(PropertyNotFoundException):
            filename = f"{http_base}/no-password.http"
            comp = self.get_request_comp(filename, target="no-password")
            comp.get_request()
            raise comp.property_util.errors[0]

    def test_certificate_available(self):
        filename = f"{http_base}/no-password.http"
        cert_file = f"{cert_base}/no-password.pem"
        req_fail = self.get_req_comp(
            filename, target="no-password", properties=["cert=", "file="]
        )
        resp_fail_400 = req_fail.get_response()
        self.assertEqual(400, resp_fail_400.status_code, "with cert, status_code ==200")
        req_comp_success = self.get_req_comp(
            filename, target="no-password", properties=[f"cert={cert_file}", "file="]
        )
        self.assertTrue(
            req_comp_success.http.certificate, "certificate should be available"
        )
        resp_200 = req_comp_success.get_response()
        self.assertEqual(
            200, resp_200.status_code, "when cert supplied, it should return 200"
        )

    def test_certificate_available2(self):
        # insecure is added just to test curl output
        filename = f"{http_base}/no-password.http"
        cert_file = f"{cert_base}/cert.crt"
        key_file = f"{cert_base}/key.key"
        req_comp = self.get_req_comp(
            filename, target="with-key-and-cert", properties=[f"cert=", f"key="]
        )
        self.assertTrue(req_comp.http.certificate, "certificate should be available")
        resp_400 = req_comp.get_response()
        self.assertEqual(
            400, resp_400.status_code, "with empty cert, status_code is 400"
        )
        req_comp2 = self.get_req_comp(
            filename,
            target="with-key-and-cert",
            properties=[f"cert={cert_file}", f"key={key_file}"],
        )
        resp_200 = req_comp2.get_response()
        self.assertTrue(req_comp2.http.certificate, "certificate should be available")
        self.assertEqual(200, resp_200.status_code, "with cert, status_code ==200")

    def test_p12(self):
        filename = f"{http_base}/no-password.http"
        p12 = f"{cert_base}/badssl.com-client.p12"
        req_comp2 = self.get_req_comp(
            filename,
            target="with-p12",
            properties=[f"p12={p12}", f"password=badssl.com"],
        )
        resp_200 = req_comp2.get_response()
        self.assertTrue(req_comp2.http.certificate, "certificate should be available")
        self.assertEqual(200, resp_200.status_code, "with cert, status_code ==200")

    def test_p12_curl(self):
        filename = f"{http_base}/no-password.http"
        p12 = f"{cert_base}/badssl.com-client.p12"
        curl_comp: CurlCompiler = self.get_req_comp(
            filename,
            target="with-p12",
            properties=[f"p12={p12}", f"password=badssl.com"],
            curl=True,
        )
        self.assertEqual(
            f"""curl -X GET --url https://client.badssl.com/ \\
--cert {quote}{p12}:badssl.com{quote} \\
--cert-type P12""",
            curl_comp.get_curl_output(),
        )

    def test_cert_curl(self):
        # insecure is added just to test curl output
        filename = f"{http_base}/no-password.http"
        cert_file = f"{cert_base}/cert.crt"
        key_file = f"{cert_base}/key.key"
        curl_comp = self.get_req_comp(
            filename,
            target="with-key-and-cert",
            properties=[f"cert={cert_file}", f"key={key_file}"],
            curl=True,
        )
        self.assertEqual(
            f"""curl -X GET --url https://client.badssl.com/ \\
--cert {quote}{cert_file}{quote} \\
--key {quote}{key_file}{quote} \\
-k""",
            curl_comp.get_curl_output(),
            "curl output with cert is not same as expected",
        )

    def test_curl_extend(self):
        filename = f"{http_base}/no-password.http"
        cert_file = f"{cert_base}/cert.crt"
        key_file = f"{cert_base}/key.key"
        req_comp = self.get_req_comp(
            filename,
            target="sample",
            properties=[f"cert={cert_file}", f"key={key_file}"],
        )
        req_comp.load()
        req_comp.load_def()
        self.assertEqual(
            req_comp.httpdef.certificate,
            [cert_file, key_file],
            "should inherit certificate",
        )
        self.assertTrue(req_comp.httpdef.session_clear, "should inherit clear")
        self.assertTrue(req_comp.httpdef.allow_insecure, "should inherit insecure")
