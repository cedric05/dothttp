import os
import unittest

from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
base_dir = f"{dir_path}/requests"
filename = f"{base_dir}/url_extend.http"


class UrlExtend(TestBase):
    def test_parent(self):
        request = self.get_request(filename, target="parent_sub")
        self.assertEqual("https://req.dothttp.dev/user/profile", request.url)

    def test_child(self):
        request = self.get_request(filename, target="child_sub")
        self.assertEqual("https://req.dothttp.dev/user/profile", request.url)

    def test_none(self):
        request = self.get_request(filename, target="none_sub")
        self.assertEqual("https://req.dothttp.dev/user/profile", request.url)

    def test_both(self):
        request = self.get_request(filename, target="both_sub")
        self.assertEqual("https://req.dothttp.dev/user/profile", request.url)

    def test_parenturlparamsinurl(self):
        request = self.get_request(filename, target="parenturlparamsinurl_sub")
        self.assertEqual("https://req.dothttp.dev/user/profile", request.url)

    def test_parenturlparamsext(self):
        request = self.get_request(filename, target="parenturlparamsext_sub")
        self.assertEqual("https://req.dothttp.dev/user/profile", request.url)

    def test_childurlparamsinurl(self):
        request = self.get_request(filename, target="childurlparamsinurl_sub")
        self.assertEqual("https://req.dothttp.dev/user/profile?ramu=ranga", request.url)

    def test_childurlparamsext(self):
        request = self.get_request(filename, target="childurlparamsext_sub")
        self.assertEqual("https://req.dothttp.dev/user/profile?ramu=ranga", request.url)

    def test_bothurlparamsext(self):
        request = self.get_request(filename, target="bothurlparamsext_sub")
        self.assertEqual("https://req.dothttp.dev/user/profile?ramu=ranga", request.url)

    def test_bothurlparamsinurl(self):
        request = self.get_request(filename, target="bothurlparamsinurl_sub")
        self.assertEqual("https://req.dothttp.dev/user/profile?ramu=ranga", request.url)

    def test_parenturlchildext(self):
        request = self.get_request(filename, target="parenturlchildext_sub")
        self.assertEqual("https://req.dothttp.dev/user/profile?ramu=ranga", request.url)

    def test_childurlparentext(self):
        request = self.get_request(filename, target="childurlparentext_sub")
        self.assertEqual("https://req.dothttp.dev/user/profile?ramu=ranga", request.url)


if __name__ == '__main__':
    unittest.main()
