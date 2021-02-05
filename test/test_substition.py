import json

from test import TestBase
from test.test_request import dir_path


class SubstitutionTest(TestBase):
    def test_substitution(self):
        req = self.get_request(f"{dir_path}/substitution/host.http")
        self.assertEqual("https://dothttp.azurewebsites.net/ram", req.url, "incorrect url")

    def test_substitution_json_query_multiple(self):
        req = self.get_request(f"{dir_path}/substitution/query.http")
        self.assertEqual("https://dothttp.azurewebsites.net/ram?key1=value1&key2=value2", req.url, "incorrect url")
        self.assertEqual(json.loads(req.body), {"key1": "value2"})

    def test_substitution4(self):
        req = self.get_request(f"{dir_path}/substitution/query.http", env=["test1", "test2"])
        self.assertEqual(json.loads(req.body), {"key1": "value2"})
        self.assertEqual('https://dothttp.azurewebsites.net/ram?key1=value1&key2=value2',
                         req.url)

    def test_substitution5(self):
        req = self.get_request(f"{dir_path}/substitution/query.http", env=["test1", "test2"],
                               prop=f"{dir_path}/substitution/prop1.json")
        self.assertEqual(json.loads(req.body), {"key1": "value2"})
        self.assertEqual('https://dothttp.azurewebsites.net/ram?key1=value1&key2=value2',
                         req.url)

    def test_substitution6(self):
        # TODO
        # comments in payload
        pass
