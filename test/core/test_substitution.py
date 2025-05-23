import json
from test import TestBase
from test.core.test_request import dir_path

from requests import PreparedRequest

from dothttp.parse import HttpFileException

base_dir = f"{dir_path}/substitution"


class SubstitutionTest(TestBase):
    def test_substitution(self):
        req = self.get_request(f"{base_dir}/host.http")
        self.assertEqual(
            "https://dothttp.azurewebsites.net/ram", req.url, "incorrect url"
        )

    def test_substitution_json_query_multiple(self):
        req = self.get_request(
            f"{base_dir}/multipleprop.http",
            prop=f"{base_dir}/multipleprop.json",
        )
        self.assertEqual(
            "https://httpbing.org/ram?haha=value1&key2=ahah", req.url, "incorrect url"
        )
        self.assertEqual(
            {"qu2": "va2"},
            json.loads(req.body),
        )

    def test_substitution_multiple_env(self, filename=f"{base_dir}/prop1.json"):
        req = self.get_request(
            f"{base_dir}/multipleenv.http", prop=filename, env=["env1", "env2"]
        )
        self.assertEqual({"qu2": "va2"}, json.loads(req.body))
        self.assertEqual("https://httpbing.org/ram?haha=value1&key2=ahah", req.url)

    def test_substitution_property_file_comments(self):
        self.test_substitution_multiple_env(f"{base_dir}/prop2.json")

    def test_substitution_with_default_prop(self):
        req = self.get_request(f"{base_dir}/httpfileprop.http")
        self.assertEqual("https://google.com/", req.url)
        self.assertEqual("GET", req.method)

    def test_substitution_commandline(self):
        req = self.get_request(
            f"{base_dir}/httpfileprop.http",
            properties=["dontsubstitute=dothttp.azurewebsites.net"],
        )
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url)
        self.assertEqual("GET", req.method)

    def test_substitution_infile_with_quotes(self):
        req: PreparedRequest = self.get_request(f"{base_dir}/infilepropwithquotes.http")
        self.assertEqual("https://google.com/", req.url)
        self.assertEqual("POST", req.method)
        self.assertEqual(b'{"key": " space in between quotes"}', req.body)

    def test_json_substition(self):
        req: PreparedRequest = self.get_request(f"{base_dir}/jsonsub.http")
        self.assertEqual("http://localhost:8000/post", req.url)
        self.assertEqual("POST", req.method)
        self.assertEqual(
            b'{"test": {"data": {"candidateID": "1117026", "isAnonymous": true}}}',
            req.body,
        )

    def test_substitution_infile_with_multiple_suages(self):
        req: PreparedRequest = self.get_request(
            f"{base_dir}/infilesinglewithmultipleusages.http"
        )
        self.assertEqual("https://google.com/", req.url)
        self.assertEqual(b'{"google.com": "google.com"}', req.body)

    def test_define_on_second_occurence(self):
        req: PreparedRequest = self.get_request(
            f"{base_dir}/definevariableonsecond.http"
        )
        self.assertEqual("https://dothttp.dev/", req.url)
        self.assertEqual("dothttp.dev", req.body)

    def test_object_substitution(self):
        req: PreparedRequest = self.get_request(
            f"{base_dir}/envvariableswithjson.http", env=["env3"]
        )
        self.assertEqual(
            b'{"object": {"key": "value"}, "int": 3, "str": "str", "null": null, "true": t'
            b'rue, "false": false, "float": 1.23}',
            req.body,
        )

    def test_only_when_required(self):
        req: PreparedRequest = self.get_request(
            f"{base_dir}/sub_with_double_sub_notused.http", target="double_def_pass"
        )
        with self.assertRaises(HttpFileException):
            req: PreparedRequest = self.get_request(
                f"{base_dir}/sub_with_double_sub_notused.http", target="double_def_fail"
            )

    def test_substitute_one_by_one(self):
        # path
        req: PreparedRequest = self.get_request(
            f"{base_dir}/header_subs.http", properties=["path=get"]
        )
        self.assertEqual("https://req.dothttp.dev/get", req.url)

        # header
        req2: PreparedRequest = self.get_request(
            f"{base_dir}/header_subs.http", properties=["path=get"], target="headers"
        )
        self.assertEqual({"get": "get"}, req2.headers)

        # basicauth
        req3: PreparedRequest = self.get_request(
            f"{base_dir}/header_subs.http", properties=["path=get"], target="auth"
        )
        self.assertEqual({"Authorization": "Basic Z2V0OmdldA=="}, req3.headers)

        # query
        req4: PreparedRequest = self.get_request(
            f"{base_dir}/header_subs.http", properties=["path=get"], target="query"
        )
        self.assertEqual("https://req.dothttp.dev/?get=get", req4.url)

        # data
        req5: PreparedRequest = self.get_request(
            f"{base_dir}/header_subs.http", properties=["path=get"], target="body"
        )
        self.assertEqual("get", req5.body)

        # files
        req6: PreparedRequest = self.get_request(
            f"{base_dir}/header_subs.http",
            properties=["path=sadfasdfasdfasdfasdfasdfasf"],
            target="files",
        )
        self.assertIn(b"sadfasdfasdfasdfasdfasdfasf", req6.body)

        # datajson
        req7: PreparedRequest = self.get_request(
            f"{base_dir}/header_subs.http", properties=["path=get"], target="data"
        )
        self.assertEqual("get=get", req7.body)

        # json
        req8: PreparedRequest = self.get_request(
            f"{base_dir}/header_subs.http", properties=["path=get"], target="json"
        )
        self.assertEqual(b'{"get": "get"}', req8.body)

    def test_substitution_preference(self):
        # command line > env (last env > first env) > infile
        req: PreparedRequest = self.get_request(
            f"{base_dir}/simpleinfile.http", prop=f"{base_dir}/simepleinfile.json"
        )
        self.assertEqual("https://google.com/", req.url)
        req: PreparedRequest = self.get_request(
            f"{base_dir}/simpleinfile.http",
            prop=f"{base_dir}/simepleinfile.json",
            env=["env1"],
        )
        self.assertEqual("https://yahoo.com/", req.url)
        req: PreparedRequest = self.get_request(
            f"{base_dir}/simpleinfile.http",
            prop=f"{base_dir}/simepleinfile.json",
            env=["env1", "env2"],
        )
        self.assertEqual("https://ins.com/", req.url)
        req: PreparedRequest = self.get_request(
            f"{base_dir}/simpleinfile.http",
            prop=f"{base_dir}/simepleinfile.json",
            env=["env1", "env2", "env3"],
        )
        self.assertEqual("https://hub.com/", req.url)
        req: PreparedRequest = self.get_request(
            f"{base_dir}/simpleinfile.http",
            prop=f"{base_dir}/simepleinfile.json",
            env=["env1", "env2", "env3"],
            properties=["host=ramba.com"],
        )
        self.assertEqual("https://ramba.com/", req.url)

    
    def test_system_command(self):
        # test system command not substitution as insecure flag is not set
        system_command_request: PreparedRequest = self.get_request(
            file=f"{base_dir}/system_command.http", target="1"
        )
        request_data = json.loads(system_command_request.body)
        self.assertNotEqual(request_data, {"sub": "hello\n"}, "insecure flag is not set")

        # test system command substitution as insecure flag is set
        system_command_request: PreparedRequest = self.get_request(
            file=f"{base_dir}/system_command.http", target="2"
        )
        request_data = json.loads(system_command_request.body)
        self.assertEquals(request_data, {"sub": "world\n"}, "insecure flag is set")


        # test system command substitution as insecure flag is base
        system_command_request: PreparedRequest = self.get_request(
            file=f"{base_dir}/system_command.http", target="parent"
        )
        request_data = json.loads(system_command_request.body)
        self.assertEquals(request_data, {"sub": "hello\n"}, "parent has insecure flag is set")



        # test system command substitution as insecure flag is grand parent
        system_command_request: PreparedRequest = self.get_request(
            file=f"{base_dir}/system_command.http", target="child"
        )
        request_data = json.loads(system_command_request.body)
        self.assertEquals(request_data, {"sub": "hello\n"}, "grand parent has insecure flag is set")


    def test_substitution_from_env_variable(self):
        # add env variable DOTHTTP_ENV_env to os.environ
        # test if substitution works 
        import os
        os.environ["DOTHTTP_ENV_env"] = "env1"
        req: PreparedRequest = self.get_request(
            f"{base_dir}//environmet_variable.http",
        )
        self.assertEqual(json.loads(req.body), {"sub": "env1"})
        del os.environ["DOTHTTP_ENV_env"]

    
    def test_math_expresssion_substitution(self):
        req: PreparedRequest = self.get_request(
            f"{base_dir}/math_expression.http",
        )
        self.assertEqual(json.loads(req.body), {"secondsInDay": "864000"})

    def test_duplicate_var(self):
        req: PreparedRequest = self.get_request(
            f"{base_dir}/duplicate_var.http",
        )
        self.assertEqual(json.loads(req.body), {"b": 10})

    
    def test_simple_index(self):
        req: PreparedRequest = self.get_request(
            f"{base_dir}/index/simple_index.http",
        )
        self.assertEqual(json.loads(req.body), {"name": "pras"})
        req: PreparedRequest = self.get_request(
            f"{base_dir}/index/simple_index2.http",
        )
        self.assertEqual(json.loads(req.body), {"name": "pras"})
        
    def test_properties_index(self):
        req: PreparedRequest = self.get_request(
            f"{base_dir}/index/property_index.http",
            properties=["propindex=name"]
        )
        self.assertEqual(json.loads(req.body), {"name": "pras"})
        

    def test_env_index(self):
        # create a temp file
        # write env and pass ti to prepared request
    
        req: PreparedRequest = self.get_request(
            f"{base_dir}/index/property_index.http",
            env=["sample"],
        )
        self.assertEqual(json.loads(req.body), {"name": 'pras'})

    def test_ref_index(self):
        req: PreparedRequest = self.get_request(
            f"{base_dir}/index/ref.http",
        )
        self.assertEqual(json.loads(req.body),  {"name": 'pras'})


    def test_ref_index(self):
        req: PreparedRequest = self.get_request(
            f"{base_dir}/duplicate_var.http",
        )
        self.assertEqual(json.loads(req.body), {"b": 10})


    def test_nested_index(self):
        req: PreparedRequest = self.get_request(
            f"{base_dir}/index/nested.http",
        )
        self.assertEqual(json.loads(req.body), {
                'attendance_status': 'present',
                'math_grade': 90,
                'sibling': {'brother': 'Tom', 'sister': 'Alice'}
                }
            )


    def test_index_error(self):
        try:
            self.get_request(
                f"{base_dir}/index/property_index.http",
            )
        except Exception as e:
            print(e)
        else:
            self.fail("expected error")
