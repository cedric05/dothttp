import unittest

from dothttp import Config, RequestCompiler, CurlCompiler, HttpFileFormatter


class TestBase(unittest.TestCase):

    @staticmethod
    def get_request(file, env=None, prop=None, properties=None):
        return TestBase.get_req_comp(file, env, prop, properties).get_request()

    @staticmethod
    def get_req_comp(file, env=None, prop=None, properties=None,
                     info=False, debug=False, curl=False,
                     format=False, stdout=False):
        if properties is None:
            properties = []
        if env is None:
            env = []
        config = Config(file=file,
                        curl=curl,
                        debug=debug,
                        property_file=prop,
                        env=env,
                        properties=properties,
                        no_cookie=False,
                        format=format,
                        stdout=stdout,
                        info=info)
        if format:
            return HttpFileFormatter(config)
        if curl:
            return CurlCompiler(config)
        else:
            return RequestCompiler(config)
