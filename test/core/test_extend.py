import os

from dothttp import UndefinedHttpToExtend, ParameterException
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
base_dir = f"{dir_path}/requests"


class ExtendTests(TestBase):
    def test_base_extend(self):
        filename = f"{base_dir}/auth_extend.http"
        request = self.get_request(filename, target="sub")
        self.assertEqual("headervalue1", request.headers.get('header1'))
        self.assertEqual("headervalue2", request.headers.get('header2'))
        self.assertEqual(
            "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
            request.headers.get('Authorization'))

    def test_grand_should_work(self):
        # recursive extend will not work
        filename = f"{base_dir}/auth_extend.http"
        request = self.get_request(filename, target="sub2")
        self.assertEqual("headervalue2", request.headers.get('header2'))
        self.assertEqual("headervalue3", request.headers.get('header3'))
        self.assertEqual(
            "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
            request.headers.get('Authorization'))

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
        # should work for any method
        # for undefined base it should throw error
        filename = f"{base_dir}/auth_extend.http"
        request = self.get_request(filename, target="use digest auth post")
        self.assertEqual("headervalue4", request.headers.get('header4'))

    def test_url_extend_from_parent(self):
        filename = f"{base_dir}/auth_extend.http"
        request = self.get_request(filename, target="query2")
        self.assertEqual(
            "http://localhost:8000/digest-auth/20202/username/password/md5?ram=raju",
            request.url)

    def test_recursive(self):
        filename = f"{base_dir}/auth_extend.http"
        with self.assertRaises(ParameterException):
            self.get_request(filename, target="recursive")

    def test_flag_extend(self):
        filename = f"{base_dir}/auth_extend.http"
        req_comp = self.get_req_comp(filename, target="argsextend")
        req_comp.load()
        req_comp.load_def()
        self.assertTrue(req_comp.httpdef.allow_insecure)
        self.assertTrue(req_comp.httpdef.session_clear)
        s1 = req_comp.get_session()
        s2 = req_comp.get_session()
        self.assertNotEqual(s1, s2)
        s1.close()
        s2.close()
