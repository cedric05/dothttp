import requests

from dothttp import PropertyNotFoundException
from test import TestBase
from test.core.test_request import dir_path

base_dir = f"{dir_path}/multi"

session = requests.session()


class Multiplefiletest(TestBase):
    testpostdata = b'{"ram": "ranga", "itsstring": "10", "itsstring2": "ramchandra", "itsint": 10, "itsint2": 29, ' \
                   b'"itsfloat": 2.3, "itstrue": true, "itsfalse": false, "itsonemoretrue": true, "itsonemorefalse": false, ' \
                   b'"itsnull": null, "itsarray": ["10", "ramchandra", 10, 29, true, false, null, 2.3]}'

    def test_simple_http(self):
        # should run as it is not using any vars
        req = self.get_request(f"{base_dir}/multi.http", target=1)
        self.assertEqual("https://req.dothttp.dev/?querykey=queryvalue", req.url)

    def test_infiledefined_data_prop_http(self):
        # should run as it is not using any vars
        req = self.get_request(f"{base_dir}/multi.http", target=2)
        self.assertEqual("https://req.dothttp.dev/?10=queryvalue", req.url)
        self.assertEqual("10=queryvalue&querykey=10", req.body)

    def test_infiledefined_json_prop_http(self):
        # should run as it is not using any vars
        req = self.get_request(f"{base_dir}/multi.http", target=3)
        self.assertEqual("https://req.dothttp.dev/?10=queryvalue", req.url)
        self.assertEqual(b'{"10": "queryvalue", "querykey": "10"}', req.body)

    def test_infiledefined_json_complex_prop_http(self):
        # should run as it is not using any vars
        req = self.get_request(f"{base_dir}/multi.http", target=4)
        self.assertEqual("https://req.dothttp.dev/?10=queryvalue", req.url)
        self.assertEqual(
            self.testpostdata,
            req.body)

    def test_infileunresolved_prop_http(self):
        # should run as it is not using any vars
        with self.assertRaises(PropertyNotFoundException):
            # should fail with unresolved properties
            self.get_request(f"{base_dir}/multi.http", target=5)
        # should pass when required properties are sent
        req = self.get_request(f"{base_dir}/multi.http",
                               target=5,
                               properties=["querykey2=10",
                                           "itsactualstring2=ramchandra",
                                           "querykey2=10",
                                           "int2=29",
                                           "float2=2.3",
                                           "true2=true",
                                           "false2=false",
                                           "null2=null",
                                           ])
        self.assertEqual("https://req.dothttp.dev/?10=queryvalue", req.url)
        self.assertEqual(
            self.testpostdata,
            req.body)
