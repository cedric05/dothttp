import os
import unittest

from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
base_dir = f"{dir_path}/requests"
filename = f"{base_dir}/url_extend.http"


class UrlExtend(TestBase):
    def test_parent(self):
        self.check_url("https://req.dothttp.dev/user/profile", "parent_sub")

    def test_child(self):
        self.check_url("https://req.dothttp.dev/user/profile", "child_sub")

    def test_none(self):
        self.check_url("https://req.dothttp.dev/user/profile", "none_sub")

    def test_both(self):
        self.check_url("https://req.dothttp.dev/user/profile", "both_sub")

    def test_parenturlparamsinurl(self):
        self.check_url("https://req.dothttp.dev/user/profile", "parenturlparamsinurl_sub")

    def test_parenturlparamsext(self):
        self.check_url("https://req.dothttp.dev/user/profile?ramu=ranga", "parenturlparamsext_sub")

    def test_childurlparamsinurl(self):
        self.check_url("https://req.dothttp.dev/user/profile?ramu=ranga", "childurlparamsinurl_sub")

    def test_childurlparamsext(self):
        self.check_url("https://req.dothttp.dev/user/profile?ramu=ranga", "childurlparamsext_sub")

    def test_bothurlparamsext(self):
        self.check_url("https://req.dothttp.dev/user/profile?rajesh=ranga&ramu=ranga", "bothurlparamsext_sub")

    def test_bothurlparamsinurl(self):
        self.check_url("https://req.dothttp.dev/user/profile?ramu=ranga", "bothurlparamsinurl_sub")

    def test_parenturlchildext(self):
        self.check_url("https://req.dothttp.dev/user/profile?ramu=ranga", "parenturlchildext_sub")

    def test_childurlparentext(self):
        self.check_url("https://req.dothttp.dev/user/profile?ramu=ranga&rajesh=ranga", "childurlparentext_sub")

    def test_childwithonlyparams(self):
        self.check_url("https://req.dothttp.dev/user/?rajesh=ranga", "childwithonlyparams_sub")

    def test_childwithonlyparamsinurl(self):
        self.check_url("https://req.dothttp.dev/user/?rajesh=ranga", "childwithonlyparamsinurl_sub")

    def test_childwithonlyparamsinurl2(self):
        self.check_url("https://req.dothttp.dev/user/?rajesh=ranga", "childwithonlyparamsinurl2_sub")

    def test_reuseurl(self):
        self.check_url("https://req.dothttp.dev/user", "reuseurl_sub")

    def test_reuseurl2(self):
        self.check_url("https://req.dothttp.dev/user/", "reuseurl2_sub")

    def test_dontuseurl(self, assert_url="https://req2.dothttp.dev/user", target="dontuseurl_sub"):
        self.check_url(assert_url, target)

    def check_url(self, assert_url, target):
        request = self.get_request(filename, target=target)
        self.assertEqual(assert_url, request.url)


if __name__ == '__main__':
    unittest.main()
