import json
import unittest

from dothttp import Config, RequestCompiler


class RequestTest(unittest.TestCase):

    def test_get(self):
        req = self.get_request("tests/requests/pass.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url, "incorrect url")
        self.assertEqual("GET", req.method, "incorrect url")

    def test_post(self):
        req = self.get_request("tests/requests/pass2.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url, "incorrect url")
        self.assertEqual("POST", req.method, "incorrect url")

    def test_query(self):
        req = self.get_request("tests/requests/query.http")
        self.assertEqual("https://dothttp.azurewebsites.net/?key3=value3&key1=value1&key2=value2", req.url,
                         "incorrect url computed")
        self.assertEqual("GET", req.method, "incorrect method")

    def test_payload(self):
        req = self.get_request("tests/requests/payload.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual("{}", req.body, "incorrect method")

    def test_payload2(self):
        req = self.get_request("tests/requests/payload2.http")
        self.assertEqual("https://dothttp.azurewebsites.net/?key3=value3&key1=value1&key2=value2", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual("{this is bad}", req.body, "incorrect method")

    def test_payload3(self):
        req = self.get_request("tests/requests/payload3.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual("{}", req.body, "incorrect method")

    def test_json_payload(self):
        req = self.get_request("tests/requests/jsonpayload.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual('{"string": "simple"}', req.body, "incorrect method")

    def test_json_payload2(self):
        req = self.get_request("tests/requests/jsonpayload2.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual(
            '{"string": "simple", "list": ["dothttp", "azure"], "null": null, "bool": false, "bool2": true, "float": 1.121212, "float2": 1.0}',
            req.body,
            "incorrect method")

    def test_json_payload3(self):
        req = self.get_request("tests/requests/jsonpayload3.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual({"menu": {
            "header": "SVG Viewer",
            "items": [
                {"id": "Open"},
                {"id": "OpenNew", "label": "Open New"},
                None,
                {"id": "ZoomIn", "label": "Zoom In"},
                {"id": "ZoomOut", "label": "Zoom Out"},
                {"id": "OriginalView", "label": "Original View"},
                None,
                {"id": "Quality"},
                {"id": "Pause"},
                {"id": "Mute"},
                None,
                {"id": "Find", "label": "Find..."},
                {"id": "FindAgain", "label": "Find Again"},
                {"id": "Copy"},
                {"id": "CopyAgain", "label": "Copy Again"},
                {"id": "CopySVG", "label": "Copy SVG"},
                {"id": "ViewSVG", "label": "View SVG"},
                {"id": "ViewSource", "label": "View Source"},
                {"id": "SaveAs", "label": "Save As"},
                None,
                {"id": "Help"},
                {"id": "About", "label": "About Adobe CVG Viewer..."}
            ]
        }}, json.loads(req.body), "json payload parsed wrong")

    def test_json_payload_complex(self):
        req = self.get_request("tests/requests/jsonpayload4.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual({
            "glossary": {
                "title": "example glossary",
                "GlossDiv": {
                    "title": "S",
                    "GlossList": {
                        "GlossEntry": {
                            "ID": "SGML",
                            "SortAs": "SGML",
                            "GlossTerm": "Standard Generalized Markup Language",
                            "Acronym": "SGML",
                            "Abbrev": "ISO 8879:1986",
                            "GlossDef": {
                                "para": "A meta-markup language, used to create markup languages such as DocBook.",
                                "GlossSeeAlso": ["GML", "XML"]
                            },
                            "GlossSee": "markup"
                        }
                    }
                }
            }
        }, json.loads(req.body), "json payload parsed wrong")

    def test_substition(self):
        # TODO
        # host, query, data
        pass

    def test_substition2(self):
        # TODO
        # json
        pass

    def test_substition3(self):
        # TODO
        # test multiple variables
        pass

    def test_substition4(self):
        # TODO
        # test multiple env
        pass

    def test_substition5(self):
        # TODO
        # test default, specifed property file
        pass

    def test_substition5(self):
        # TODO
        # comments in payload
        pass

    @staticmethod
    def get_request(file):
        config = Config(file=file, curl=False, debug=False, property_file=None, env=[])
        req = RequestCompiler(config).get_request()
        return req


if __name__ == "__main__":
    unittest.main()
