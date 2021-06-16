import os
from pathlib import Path

from dotextensions.server import Command
from dotextensions.server.commands import TypeFromPos
from test import TestBase

dir_path = os.path.dirname(os.path.realpath(__file__))
command_dir = Path(f"{dir_path}/commands")


class TypePositionTest(TestBase):
    def setUp(self) -> None:
        self.execute_handler = TypeFromPos()

    def test_params_fail(self):
        self.assertTrue(
            self.execute_handler.run(
                Command(id=1,
                        method=TypeFromPos.name,
                        params={}
                        )
            ).result.get("error"))

    def test_working(self):
        self.assertTrue(
            self.execute_handler.run(
                Command(id=1,
                        method=TypeFromPos.name,
                        params={
                            "position": 20,
                            "filename": command_dir.joinpath("complexrun.http")
                        }
                        )
            ).result.get("error"))
