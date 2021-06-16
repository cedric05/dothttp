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
        self.assertTrue(self.execute_n_get({}).get("error"))

    def test_working(self):
        params = {
            "position": 34,
            "filename": str(command_dir.joinpath("complexrun.http"))
        }
        result = self.execute_n_get(params)
        self.assertEqual({'base_start': None, 'target': '1', 'target_base': None, 'type': 'url'}, result)

    # def test_exhaust(self):
    #     for i in range(0, 290):
    #         result = self.execute_n_get(params={"position": i, "filename": command_dir.joinpath("complexrun.http")})
    #         print(result)
    #         self.assertFalse(result.get("error"))

    def execute_n_get(self, params):
        return self.execute_handler.run(
            Command(id=1,
                    method=TypeFromPos.name,
                    params=params
                    )
        ).result
