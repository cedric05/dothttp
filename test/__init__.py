import unittest

from dothttp import Config, RequestCompiler


class TestBase(unittest.TestCase):

    @staticmethod
    def get_request(file, env=None, prop=None, properties=None):
        if properties is None:
            properties = []
        if env is None:
            env = []
        config = Config(file=file,
                        curl=False,
                        debug=False,
                        property_file=prop,
                        env=env,
                        properties=properties,
                        no_cookie=False,
                        format=False,
                        info=False)
        req = RequestCompiler(config).get_request()
        return req
