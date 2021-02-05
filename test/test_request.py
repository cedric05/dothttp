import os
import unittest

from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))


class RequestTest(TestBase):
    def test_get(self):
        req = self.get_request(f"{dir_path}/requests/pass.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url, "incorrect url")
        self.assertEqual("GET", req.method, "incorrect url")

    def test_post(self):
        req = self.get_request(f"{dir_path}/requests/pass2.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url, "incorrect url")
        self.assertEqual("POST", req.method, "incorrect url")

    def test_query(self):
        req = self.get_request(f"{dir_path}/requests/query.http")
        self.assertEqual("https://dothttp.azurewebsites.net/?key3=value3&key1=value1&key2=value2", req.url,
                         "incorrect url computed")
        self.assertEqual("GET", req.method, "incorrect method")

if __name__ == "__main__":
    unittest.main()
