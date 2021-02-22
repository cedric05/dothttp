import json

from test import TestBase
from test.test_request import dir_path

base_dir = f"{dir_path}/substitution"


class SubstitutionTest(TestBase):
    def test_substitution(self):
        req = self.get_request(f"{base_dir}/host.http")
        self.assertEqual("https://dothttp.azurewebsites.net/ram", req.url, "incorrect url")

    def test_substitution_json_query_multiple(self):
        req = self.get_request(f"{base_dir}/multipleprop.http",
                               prop=f"{base_dir}/multipleprop.json", )
        self.assertEqual("https://httpbing.org/ram?haha=value1&key2=ahah", req.url, "incorrect url")
        self.assertEqual({"qu2": "va2"}, json.loads(req.body), )

    def test_substitution_multiple_env(self, filename=f"{base_dir}/prop1.json"):
        req = self.get_request(f"{base_dir}/multipleenv.http",
                               prop=filename,
                               env=["env1", "env2"])
        self.assertEqual({"qu2": "va2"}, json.loads(req.body))
        self.assertEqual('https://httpbing.org/ram?haha=value1&key2=ahah',
                         req.url)

    def test_substitution_property_file_comments(self):
        self.test_substitution_multiple_env(f"{base_dir}/prop2.json")
