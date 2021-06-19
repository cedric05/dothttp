import json
import os
import tempfile
from pathlib import Path

from dotextensions.server.handlers.http2postman import Http2Postman
from dotextensions.server.models import Command
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
command_dir = Path(f"{dir_path}/commands")


class TypePositionTest(TestBase):
    def setUp(self) -> None:
        self.execute_handler = Http2Postman()

    def test_simple(self):
        with tempfile.TemporaryDirectory() as f:
            with open(os.path.join(command_dir, "export1.postman.json")) as f2:
                data = json.load(f2)
            result = self.execute_handler.run(command=Command(
                method=self.execute_handler.name,
                id=92,
                params={"filename": os.path.join(command_dir, "swagger2har_petstore_response.http"), "directory": f}))
            self.assertEqual(data, result.result)
