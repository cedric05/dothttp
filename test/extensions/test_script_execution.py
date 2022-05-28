import os
from typing import Dict
from unittest import skip

from dotextensions.server.handlers.basic_handlers import RunHttpFileHandler
from dotextensions.server.models import Command
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
command_dir = f"{dir_path}/commands"


class ScriptExecutionTest(TestBase):
    def setUp(self) -> None:
        self.execute_handler = RunHttpFileHandler()

    def test_execute_script1(self):
        result = self.execute_target("1")
        self.assertEqual({'compiled': True,
                          'error': '',
                          'properties': {'outputval': 'User-agent: *\nDisallow: /deny\n'},
                          'stdout': '',
                          'tests': [{'error': 'content-type is json',
                                     'name': 'check json',
                                     'success': False, 'result': None},
                                    {'name': 'check status', 'result': None, 'success': True, "error": None}]},
                         result.result['script_result'])

    def test_execute_script2(self):
        result = self.execute_target("2")
        self.assertEqual({'compiled': True,
                          'error': '',
                          'properties': {'outputval': 'secret_token'},
                          'stdout': 'this is sample log\n',
                          'tests': [{'name': 'check headers', 'result': None, 'success': True, "error": None},
                                    {'name': 'check status', 'result': None, 'success': True, "error": None}]},
                         result.result['script_result'])

    def test_execute_is_equals_script3(self):
        result = self.execute_target("3")
        self.assertEqual({'compiled': True,
                          'error': '',
                          'properties': {},
                          'stdout': '',
                          'tests': [{'name': 'checks payload output recursive',
                                     'result': None,
                                     'error': None,
                                     'success': True}]},
                         result.result['script_result'])

    def test_execute_delete_property_script(self):
        value = "this is before"
        result = self.execute_target("delete property", properties={
                                     "setPropertyByfile": value})
        self.assertEqual({'compiled': True,
                          'error': '',
                          'properties': {'setPropertyByfile': ''},
                          'stdout': f'value is `{value}`\n',
                          'tests': []},
                         result.result['script_result'])

    @skip("nodejs has to be setup before testing this")
    def test_execute_require_check(self):
        result = self.execute_target("require check", )
        self.assertEqual({'compiled': True,
                          'error': '',
                          'properties': {},
                          'stdout': 'value is `Hello, World!`\n',
                          'tests': []},
                         result.result['script_result'])

    def test_execute_error(self):
        result = self.execute_target("script error", )
        self.assertEqual({'compiled': True,
                          'error': '',
                          'properties': {},
                          'stdout': 'error TypeError: Undefined and null dont have properties (tried '
                                    "getting property 'out')\n",
                          'tests': []},
                         result.result['script_result'])

    def execute_target(self, target, properties=None):
        if properties is None:
            properties = {}
        result = self.execute_handler.run(Command(
            method=RunHttpFileHandler.name,
            params={
                "file": f"{command_dir}/script.http",
                "target": target,
                "properties": properties,
            },
            id=1)
        )
        return result
