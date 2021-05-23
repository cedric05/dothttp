import json

import requests

from test import TestBase
from test.core.test_request import dir_path

base_dir = f"{dir_path}/curl-like"

session = requests.session()


class PayLoadTest(TestBase):
    def test_curl_like_headers(self):
        req = self.get_request(f"{base_dir}/curllike.http")
        self.assertEqual({'simplekey1': 'simplevalue1', 'simplekey2': 'simplevalue2', 'simple-key3': 'simplevalue3',
                          'simple-key4': 'simplevalue4', 'simplekey5': 'simplevalue5', 'simplekey6': 'simplevalue6',
                          'simple-key7': 'simplevalue7',
                          'simple-key8': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                          'simplekey9': 'var',
                          'simplekey10': 'var'},
                         req.headers)

    def test_single_line(self):
        req = self.get_request(f"{base_dir}/curllike.http", target='2')
        self.assertEqual('this is example', req.body)

    def test_multiline(self):
        req = self.get_request(f"{base_dir}/curllike.http", target='3')
        self.assertEqual("""this is
multiline
var
example""", req.body)
