import os

from dothttp import UndefinedHttpToExtend
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
base_dir = f"{dir_path}/requests"


class ExtendTests(TestBase):
    def test_base_extend(self):
        filename = f"{base_dir}/auth_extend.http"
        request = self.get_request(filename, target="sub")
        self.assertEqual("headervalue1", request.headers.get('header1'))
        self.assertEqual("headervalue2", request.headers.get('header2'))
        self.assertEqual("Basic dXNlcm5hbWU6cGFzc3dvcmQ=", request.headers.get('Authorization'))

    def test_grand_shountwork(self):
        # recursive extend will not work
        filename = f"{base_dir}/auth_extend.http"
        request = self.get_request(filename, target="sub2")
        self.assertEqual("headervalue2", request.headers.get('header2'))
        self.assertEqual("headervalue3", request.headers.get('header3'))
        self.assertEqual(None, request.headers.get('Authorization'))

    def test_should_throw_in_case_of_undefined(self):
        # for undefined base it should throw error
        filename = f"{base_dir}/auth_extend.http"
        with self.assertRaises(UndefinedHttpToExtend):
            self.get_request(filename, target="sub3")

    def test_digest_auth_get(self):
        # for undefined base it should throw error
        filename = f"{base_dir}/auth_extend.http"
        request = self.get_request(filename, target="use digest auth")
        self.assertEqual("headervalue4", request.headers.get('header4'))

    def test_digest_auth_post(self):
        ## should work for any method
        # for undefined base it should throw error
        filename = f"{base_dir}/auth_extend.http"
        request = self.get_request(filename, target="use digest auth post")
        self.assertEqual("headervalue4", request.headers.get('header4'))

    def test_query_shoudnt_pass(self):
        filename = f"{base_dir}/auth_extend.http"
        request = self.get_request(filename, target="query2")
        self.assertEqual("https://httpbin.org/digest-auth/20202/username/password/md5", request.url)
