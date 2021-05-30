from dotextensions.server.commands import *
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
                                     'success': False},
                                    {'name': 'check status', 'result': None, 'success': True}]},
                         result.result['script_result'])

    def test_execute_script2(self):
        result = self.execute_target("2")
        self.assertEqual({'compiled': True,
                          'error': '',
                          'properties': {'outputval': 'secret_token'},
                          'stdout': 'this is sample log\n',
                          'tests': [{'name': 'check headers', 'result': None, 'success': True},
                                    {'name': 'check status', 'result': None, 'success': True}]},
                         result.result['script_result'])

    def test_execute_is_equals_script3(self):
        result = self.execute_target("3")
        self.assertEqual({'compiled': True,
                          'error': '',
                          'properties': {},
                          'stdout': '',
                          'tests': [{'name': 'checks payload output recursive',
                                     'result': None,
                                     'success': True}]},
                         result.result['script_result'])

    def execute_target(self, target):
        result = self.execute_handler.run(Command(
            method=RunHttpFileHandler.name,
            params={
                "file": f"{command_dir}/script.http",
                "target": target
            },
            id=1)
        )
        return result
