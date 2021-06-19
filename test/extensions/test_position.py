import os
from pathlib import Path

from dotextensions.server.handlers.gohandler import TypeFromPos
from dotextensions.server.models import Command
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

    def test_more1(self):
        for params, result in [
            ((54, 'complexrun.http'),
             {'type': 'url', 'target': '1', 'target_base': None, 'base_start': None}),
            ((154, 'complexrun.http'),
             {'type': 'url', 'target': '3', 'target_base': None, 'base_start': None}),
            ((193, 'complexrun.http'),
             {'type': 'urlparams', 'target': '3', 'target_base': None, 'base_start': None}),
            ((210, 'complexrun.http'),
             {'type': 'name', 'target': 'basicauth', 'target_base': None, 'base_start': None}),
            ((237, 'complexrun.http'),
             {'type': 'url', 'target': 'basicauth', 'target_base': None, 'base_start': None}),
            ((268, 'complexrun.http'),
             {'type': 'basic_auth', 'target': 'basicauth', 'target_base': None, 'base_start': None})
        ]:
            self.assertEqual(result, self.execute_n_get(params={"position": params[0], "filename": str(
                command_dir.joinpath(params[1]))}))

    def test_more2(self):
        for params, result in [
            ((132, 'payload.http'),
             {'type': 'payload_urlencoded', 'target': 'urlencode', 'target_base': None,
              'base_start': None}),
            ((291, 'payload.http'),
             {'type': 'payload_data', 'target': 'text-other-content', 'target_base': None,
              'base_start': None}),
            ((517, 'payload.http'),
             {'type': 'header', 'target': 'headers', 'target_base': None, 'base_start': None}),
            ((587, 'payload.http'),
             {'type': 'payload_multipart', 'target': 'files2', 'target_base': None,
              'base_start': None}),
            ((1131, 'script.http'),
             {'type': 'payload_json', 'target': 'isEquals check', 'target_base': None,
              'base_start': None}),
            ((1215, 'script.http'),
             {'type': 'script', 'target': 'isEquals check', 'target_base': None,
              'base_start': None}),
            ((682, 'payload.http'),
             {'type': 'digest_auth', 'target': 'fileinput', 'target_base': None,
              'base_start': None}),
            ((629, 'payload.http'),
             {'type': 'extra_args', 'target': 'fileinput', 'target_base': None,
              'base_start': None}),
            ((705, 'payload.http'),
             {'type': 'certificate', 'target': 'fileinput', 'target_base': None,
              'base_start': None}),
            ((747, 'payload.http'),
             {'type': 'payload_file_input', 'target': 'fileinput', 'target_base': None,
              'base_start': None}),

        ]:
            # print(({"position": params[0], "filename": params[1]},
            #        self.execute_n_get(params={"position": params[0], "filename": str(
            #            command_dir.joinpath(params[1]))})))
            self.assertEqual(result, self.execute_n_get(params={"position": params[0], "filename": str(
                command_dir.joinpath(params[1]))}))

    # def test_more3(self):
    #     for file_name in ("payload.http",
    #                       ):
    #         with open(command_dir.joinpath(file_name)) as f:
    #             count = len(f.read())
    #         for i in range(count):
    #             print(((i, file_name),
    #                    self.execute_n_get({"position": i, "filename": str(command_dir.joinpath(file_name))})))

    def execute_n_get(self, params):
        return self.execute_handler.run(
            Command(id=1,
                    method=TypeFromPos.name,
                    params=params
                    )
        ).result
