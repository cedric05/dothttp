import os
import tempfile

from dotextensions.server.handlers.har2httphandler import Har2HttpHandler
from dotextensions.server.models import Command
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
command_dir = f"{dir_path}/commands"


class ScriptExecutionTest(TestBase):
    def setUp(self) -> None:
        self.execute_handler = Har2HttpHandler()

    def test_simple(self):
        join = os.path.join(command_dir, "swagger2har_petstore_response.json")
        with tempfile.TemporaryDirectory() as directory:
            command = Command(id=1, method=Har2HttpHandler.name, params={"filename": join,
                                                                         "save_directory": directory})
            response = self.execute_handler.run(command)
            with open(os.path.join(command_dir, "har_import.http"
                                   ), 'r') as f:
                self.assertEqual(f.read(), response.result.get('http', ""))
