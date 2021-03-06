import json

from requests import PreparedRequest

from test import TestBase
from test.core.test_request import dir_path

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

    def test_substitution_with_default_prop(self):
        req = self.get_request(f"{base_dir}/httpfileprop.http")
        self.assertEqual("https://google.com/", req.url)
        self.assertEqual("GET", req.method)

    def test_substitution_commandline(self):
        req = self.get_request(f"{base_dir}/httpfileprop.http", properties=["dontsubstitute=dothttp.azurewebsites.net"])
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url)
        self.assertEqual("GET", req.method)

    def test_substitution_infile_with_quotes(self):
        req: PreparedRequest = self.get_request(f"{base_dir}/infilepropwithquotes.http")
        self.assertEqual("https://google.com/", req.url)
        self.assertEqual("POST", req.method)
        self.assertEqual(b'{"key": " space in between quotes"}', req.body)

    def test_substitution_infile_with_multiple_suages(self):
        req: PreparedRequest = self.get_request(f"{base_dir}/infilesinglewithmultipleusages.http")
        self.assertEqual("https://google.com/", req.url)
        self.assertEqual(b'{"google.com": "google.com"}', req.body)

    def test_define_on_second_occurence(self):
        req: PreparedRequest = self.get_request(f"{base_dir}/definevariableonsecond.http")
        self.assertEqual("https://dothttp.dev/", req.url)
        self.assertEqual('dothttp.dev', req.body)

    def test_substitution_preference(self):
        ## command line > env (last env > first env) > infile
        req: PreparedRequest = self.get_request(f"{base_dir}/simpleinfile.http", prop=f"{base_dir}/simepleinfile.json")
        self.assertEqual("https://google.com/", req.url)
        req: PreparedRequest = self.get_request(f"{base_dir}/simpleinfile.http",
                                                prop=f"{base_dir}/simepleinfile.json",
                                                env=["env1"]
                                                )
        self.assertEqual("https://yahoo.com/", req.url)
        req: PreparedRequest = self.get_request(f"{base_dir}/simpleinfile.http",
                                                prop=f"{base_dir}/simepleinfile.json",
                                                env=["env1", "env2"]
                                                )
        self.assertEqual("https://ins.com/", req.url)
        req: PreparedRequest = self.get_request(f"{base_dir}/simpleinfile.http",
                                                prop=f"{base_dir}/simepleinfile.json",
                                                env=["env1", "env2", "env3"]
                                                )
        self.assertEqual("https://hub.com/", req.url)
        req: PreparedRequest = self.get_request(f"{base_dir}/simpleinfile.http",
                                                prop=f"{base_dir}/simepleinfile.json",
                                                env=["env1", "env2", "env3"],
                                                properties=["host=ramba.com"]
                                                )
        self.assertEqual("https://ramba.com/", req.url)
