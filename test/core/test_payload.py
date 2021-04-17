import json
import os
import tempfile

import requests

from test import TestBase
from test.core.test_request import dir_path

base_dir = f"{dir_path}/payload"

session = requests.session()


class PayLoadTest(TestBase):
    def test_json_payload(self):
        req = self.get_request(f"{base_dir}/jsonpayload.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual(b'{"string": "simple"}', req.body, "incorrect method")

    def test_json_payload2(self):
        req = self.get_request(f"{base_dir}/jsonpayload2.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual(
            b'{"string": "simple", "list": ["dothttp", "azure"], "null": null, "bool": false, "bool2": true, "float": 1.121212, "float2": 1.0}',
            req.body,
            "incorrect method")

    def test_json_payload3(self):
        req = self.get_request(f"{base_dir}/jsonpayload3.http")
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
        }}, json.loads(req.body), "json Payload parsed wrong")

    def test_json_payload_complex(self):
        req = self.get_request(f"{base_dir}/jsonpayload4.http")
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
        }, json.loads(req.body), "json Payload parsed wrong")
        self.assertEqual('application/json', req.headers['content-type'])

    def test_payload(self):
        req = self.get_request(f"{base_dir}/payload.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual("{}", req.body, "incorrect method")

    def test_payload2(self):
        req = self.get_request(f"{base_dir}/payload2.http")
        self.assertEqual("https://dothttp.azurewebsites.net/?key3=value3&key1=value1&key2=value2", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual("{this is bad}", req.body, "incorrect method")

    def test_payload3(self):
        req = self.get_request(f"{base_dir}/payload3.http")
        self.assertEqual("https://dothttp.azurewebsites.net/", req.url,
                         "incorrect url computed")
        self.assertEqual("POST", req.method, "incorrect method")
        self.assertEqual(b"{}", req.body, "incorrect method")

    def test_file_payload(self):
        loadfile = tempfile.NamedTemporaryFile(delete=False)
        test = b"test"
        loadfile.write(test)
        loadfile.flush()
        req = self.get_request(f"{base_dir}/filepayload.http", properties=[f"filename={loadfile.name}"])
        self.assertEqual(test, req.body)
        loadfile.close()
        os.unlink(loadfile.name)

    def test_data_json_payload(self):
        req = self.get_request(f"{base_dir}/dataasformpayload.http")
        self.assertEqual("hi=prasanth", req.body)
        self.assertEqual('application/x-www-form-urlencoded', req.headers.get("content-type"))

    def test_multipart_payload(self):
        loadfile = tempfile.NamedTemporaryFile(delete=False)
        test = b"test"
        loadfile.write(test)
        loadfile.flush()
        data = f"this is text part"
        req = self.get_request(f"{base_dir}/multipartfiles.http", properties=
        [f"filename={loadfile.name}",
         f"data={data}"
         ])
        self.assertIn(test, req.body)
        self.assertIn(data.encode("utf-8"), req.body)

        # including integration test here

        req2 = self.get_request(f"{base_dir}/multipartfiles2.http", properties=
        [f"filename={loadfile.name}",
         f"data={data}"
         ])

        resp = session.send(req2).json()
        self.assertEqual(resp['files'], {'resume': 'test'})
        self.assertEqual(resp['form'], {'content2': 'this is text part'})

        loadfile.close()
        os.unlink(loadfile.name)

    def test_data_json_payload(self):
        req = self.get_request(f"{base_dir}/quoted.http")
        self.assertEqual("""
"'this can have quotes with escape sequence'"

""", req.body)

    def test_data_json_payload(self):
        req = self.get_request(f"{base_dir}/quoted2.http")
        self.assertEqual("""
"'this can have quotes with escape sequence'"

""", req.body)
