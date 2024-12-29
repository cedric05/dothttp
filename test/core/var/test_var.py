import json
from test import TestBase
from test.core.test_request import dir_path

from urllib.parse import urlparse

base_dir = f"{dir_path}/var"


class VarSubstitutionTest(TestBase):
    def test_substitution(self):
        req = self.get_request(f"{base_dir}/host.http")
        self.assertEqual("https://httpbin.org/?a=10&b=20",
                         req.url, "incorrect url")

    def test_math(self):
        req = self.get_request(f"{base_dir}/math.http")
        self.assertEqual(
            {"secInDay": "86400", "secInHour": 3600},
            json.loads(req.body),
            "incorrect body",
        )

    def test_json(self):
        req = self.get_request(f"{base_dir}/json.http")
        self.assertEqual(
            {
                'jsonData': {
                    'secInDay': 86400,
                    'secInHour': 3600,
                    "true": True,
                    "false": False,
                    "nested": [
                        1, 2, 4.4, "string", True, False, None, {
                            "key": "value"
                        }
                    ],
                    "nestedObject": {
                        "key": {
                            "key": "value"
                        }
                    }
                },
                "okay": "okay",
                "nested": {
                    'jsonData': {
                        'secInDay': 86400,
                        'secInHour': 3600,
                        "true": True,
                        "false": False,
                        "nested": [
                            1, 2, 4.4, "string", True, False, None, {
                                "key": "value"
                            }
                        ],
                        "nestedObject": {
                            "key": {
                                "key": "value"
                            }
                        }

                    },
                    "okay": "okay"
                }
            },
            json.loads(req.body),
            "incorrect body",
        )

    def test_import_sub(self):
        req = self.get_request(f"{base_dir}/child.http")
        self.assertEqual(
            {
                "a": "a",
                "b": "b",
                "c": "c",
                "d": True,
                "d2": "True",
                "jsonData": {
                    "secInDay": 86400,
                }
            },
            json.loads(req.body),
            "incorrect body",
        )

    def test_import_nested(self):
        req = self.get_request(f"{base_dir}/grand_child.http")
        self.assertEqual(
            {
                "a": "a",
                "b": "b",
                "c": "c",
                "d": True,
                "d2": "True",
                "jsonData": {
                    "secInDay": 86400,
                },
                "secInDay": '86400',
            },
            json.loads(req.body),
            "incorrect body",
        )

    def test_sub_external_command_properties(self):
        req = self.get_request(
            f"{base_dir}/grand_child.http", properties={"secInDay=0"})
        self.assertEqual(
            {
                "a": "a",
                "b": "b",
                "c": "c",
                "d": True,
                "d2": "True",
                "jsonData": {
                    "secInDay": 86400,
                },
                "secInDay": '0',
            },
            json.loads(req.body),
            "incorrect body",
        )

    def test_sub_external_env_properties(self):
        req = self.get_request(f"{base_dir}/grand_child.http", env=["test"])
        self.assertEqual(
            {
                "a": "b",
                "b": "b",
                "c": "c",
                "d": True,
                "d2": "True",
                "jsonData": {
                    "secInDay": 86400,
                },
                "secInDay": '86400',
            },
            json.loads(req.body),
            "incorrect body",
        )

    def test_override(self):
        req = self.get_request(f"{base_dir}/override.http", )
        self.assertEqual(
            {
                "a": 10,
            },
            json.loads(req.body),
            "incorrect body",
        )


    def test_var_templating(self):
        req = self.get_request(f"{base_dir}/templating.http")
        self.assertEqual(
            {
                "a":10,
                "b": "10 +  10 = 20"
            },
            json.loads(req.body),
            "incorrect body",
        )
        # parse url and get query c
        parsed = urlparse(req.url)
        # c=randomstrs 
        # total 12 = 10 (generated) + 2 (c=)
        self.assertEqual(len(parsed.query), 12)