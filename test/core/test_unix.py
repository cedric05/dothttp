# tests unix socket dothttp apis
import sys
from unittest import skipIf

import requests

from dothttp.request_base import RequestCompiler, CurlCompiler
from test import TestBase
from test.core.test_request import dir_path

try:
    import requests_unixsocket
except:
    requests_unixsocket = None

base_dir = f"{dir_path}/requests"


@skipIf(requests_unixsocket is None or not sys.platform.startswith("linux"), "in wasm mode, it will not be available")
class TestUnixSocketRequests(TestBase):
    def test_simple(self):
        request = self.get_request(
            file=f"{base_dir}/unix.http"
        )
        self.assertEqual(request.url, "http+unix://%2Fvar%2Frun%2Fdocker.sock/info")

    def test_integration(self):
        from requests_unixsocket.testutils import UnixSocketServerThread
        with UnixSocketServerThread() as usock_thread:
            urlencoded_usock = requests.compat.quote_plus(usock_thread.usock)
            base_url = f"http+unix://{urlencoded_usock}"
            req_comp: RequestCompiler = self.get_req_comp(
                file=f"{base_dir}/unix.http"
                , properties=["base_url=" + base_url]
                , target=2
            )
            response = req_comp.get_response()
            self.assertEqual(base_url + "/", response.url, "should be same request unix socket url")
            self.assertEqual(200, response.status_code, "should be 200")
            self.assertEqual('waitress', response.headers['server'], "server should be waitress")
            self.assertEqual(usock_thread.usock, response.headers['X-Socket-Path'], "unix socket path should be same")

    def test_url_extend_and_query(self):
        from requests_unixsocket.testutils import UnixSocketServerThread
        with UnixSocketServerThread() as usock_thread:
            urlencoded_usock = requests.compat.quote_plus(usock_thread.usock)
            base_url = f"http+unix://{urlencoded_usock}"
            req_comp2: RequestCompiler = self.get_req_comp(
                file=f"{base_dir}/unix.http"
                , properties=["base_url=" + base_url, "urlpath=/"]
                , target=3
            )
            response2 = req_comp2.get_response()
            self.assertEqual(200, response2.status_code, "should be 200")
            self.assertEqual('waitress', response2.headers['server'], "server should be waitress")
            self.assertEqual(usock_thread.usock, response2.headers['X-Socket-Path'], "unix socket path should be same")
            self.assertEqual('/containers/nginx/logs/', response2.headers['X-Requested-Path'],
                             "path should be same")
            self.assertEqual('timestamp=true', response2.headers['X-Requested-Query-String'])

    def test_curl(self):
        request: CurlCompiler = self.get_req_comp(
            file=f"{base_dir}/unix.http",
            curl=True
        )
        self.assertEqual("""curl -X GET --url http://localhost/info \\
--unix-socket /var/run/docker.sock""", request.get_curl_output())

    def test_curl_with_query_and_path(self):
        request: CurlCompiler = self.get_req_comp(
            file=f"{base_dir}/unix.http",
            target=3
            , properties=["base_url=" + "http+unix://%2Fvar%2Frun%2Fdocker.sock", "urlpath=/"],
            curl=True
        )
        self.assertEqual("""curl -X GET --url http://localhost/containers/nginx/logs/?timestamp=true \\
--unix-socket /var/run/docker.sock""", request.get_curl_output())
