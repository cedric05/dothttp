import unittest

from dothttp import Config, RequestCompiler


class TestBase(unittest.TestCase):

    @staticmethod
    def get_request(file, env=[], prop=None):
        config = Config(file=file, curl=False, debug=False, property_file=prop, env=env)
        req = RequestCompiler(config).get_request()
        return req
