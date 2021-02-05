import unittest

from dothttp import Config, RequestCompiler


class RequestTest(unittest.TestCase):

    def test_get(self):
        req = self.get_request("tests/requests/pass.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url, "incorrect url")
        self.assertEqual("GET", req.method, "incorrect url")

    def test_post(self):
        req = self.get_request("tests/requests/pass2.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url, "incorrect url")
        self.assertEqual("POST", req.method, "incorrect url")

    def test_query(self):
        req = self.get_request("tests/requests/query.http")
        self.assertEqual("https://dothttp.azurewebsites.net/?key3=value3&key1=value1&key2=value2", req.url,
                         "incorrect url computed")
        self.assertEqual("GET", req.method, "incorrect method")

    def test_payload(self):
        req = self.get_request("tests/requests/payload.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual("{}", req.body, "incorrect method")

    def test_payload2(self):
        req = self.get_request("tests/requests/payload2.http")
        self.assertEqual("https://dothttp.azurewebsites.net/?key3=value3&key1=value1&key2=value2", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual("{this is bad}", req.body, "incorrect method")

    def test_payload3(self):
        req = self.get_request("tests/requests/payload3.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual("{}", req.body, "incorrect method")

    def test_json_payload(self):
        req = self.get_request("tests/requests/jsonpayload.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual('{"string": "simple"}', req.body, "incorrect method")

    def test_json_payload2(self):
        req = self.get_request("tests/requests/jsonpayload2.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual(
            '{"string": "simple", "list": ["dothttp", "azure"], "null": null, "bool": false, "bool2": true, "float": 1.121212, "float2": 1.0}',
            req.body,
            "incorrect method")

    @staticmethod
    def get_request(file):
        config = Config(file=file, curl=False, debug=False, property_file=None, env=[])
        req = RequestCompiler(config).get_request()
        return req


if __name__ == "__main__":
    unittest.main()
