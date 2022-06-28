from unittest import TestCase

from requests import Response
from dothttp import HttpDef
from dothttp import js3py
from dothttp.js3py import ScriptExecutionPython
from dothttp.parse_models import ScriptType
from dothttp.property_util import PropertyProvider
from test import TestBase
from test.core.test_request import dir_path

file_name = f"{dir_path}/requests/script.http"


# integration test
class ScriptExecutionIntegrationTest(TestBase):

    def test_python(self):
        req, result = self.load_comp("python_class")
        self.assertEqual(ScriptType.PYTHON, req.httpdef.test_script_lang)
        self.assertEqual(
            {
                "stdout":
                "working\n",
                "error":
                "",
                "properties": {},
                "tests": [{
                    "name": "test_hai (test_script.SampleTest)",
                    "success": True,
                    "result": None,
                    "error": None
                }],
                "compiled":
                True
            }, result)

    def test_python_iter(self):
        req, result = self.load_comp("python iter")
        self.assertEqual(ScriptType.PYTHON, req.httpdef.test_script_lang)
        self.assertEqual(
            {
                "stdout":
                """something
something
something
something
something
something
something
something
something
something
""",
                "error":
                "",
                "properties": {},
                "tests": [{
                    "name": "test_iter",
                    "success": True,
                    "result": None,
                    "error": None
                }],
                "compiled":
                True
            }, result)

    def test_python_func(self):
        req, result = self.load_comp("python_function")
        self.assertEqual(ScriptType.PYTHON, req.httpdef.test_script_lang)
        self.assertEqual(
            {
                "stdout":
                "working\n",
                "error":
                "",
                "properties": {},
                "tests": [{
                    "name": "test_hai",
                    "success": True,
                    "result": None,
                    "error": None
                }],
                "compiled":
                True
            }, result)

    def test_javascript(self):
        req, result = self.load_comp("javascript")
        self.assertEqual(ScriptType.JAVA_SCRIPT, req.httpdef.test_script_lang)
        self.assertEqual(
            {
                "stdout":
                "",
                "error":
                "",
                "properties": {},
                "tests": [{
                    "name": "check status",
                    "success": True,
                    "result": None,
                    "error": None
                }],
                "compiled":
                True
            }, result)

    def test_javascript_default(self):
        req, result = self.load_comp("default_javascript")
        self.assertEqual(ScriptType.JAVA_SCRIPT, req.httpdef.test_script_lang)
        self.assertEqual(
            {
                "stdout":
                "",
                "error":
                "",
                "properties": {},
                "tests": [{
                    "name": "check status",
                    "success": True,
                    "result": None,
                    "error": None
                }],
                "compiled":
                True
            }, result)

    def load_comp(self, target):
        req = self.get_req_comp(file_name, target=target)
        req.load_def()
        execution_cls = js3py.ScriptExecutionJs if req.httpdef.test_script_lang == ScriptType.JAVA_SCRIPT else js3py.ScriptExecutionPython
        script_execution = execution_cls(req.httpdef, req.property_util)
        resp = req.get_response()
        return req, script_execution.execute_test_script(resp).as_json()


class ScriptExecutionIntegration(TestCase):

    def test_positive(self):
        resp = self.get_script_exe("""
class SampleTestCase(unittest.TestCase):
    def test_status_code(self):
        self.assertEquals(200 , client.response.status_code)
""")

        self.assertEqual(
            {
                'compiled':
                True,
                'error':
                '',
                'properties': {},
                'stdout':
                '',
                'tests': [{
                    'name': 'test_status_code (test_script.SampleTestCase)',
                    'success': True,
                    'result': None,
                    'error': None
                }]
            }, resp.as_json())

    def get_script_exe(self, script):
        resp = Response()
        resp.status_code = 200
        resp.headers = {"sample_header": "sample_value"}
        httpdef = HttpDef()
        httpdef.test_script = script
        script_exe = ScriptExecutionPython(httpdef, PropertyProvider())
        return script_exe.execute_test_script(resp)

    def test_pre_request(self):
        httpdef = HttpDef()
        httpdef.headers = {}
        httpdef.test_script = """
def pre_request():
    client.request.headers.setdefault('ram', 'ranga')
    client.properties.setdefault("new", "value")
"""
        props = PropertyProvider()
        props.add_command_property("ram", "raju")
        script_exe = ScriptExecutionPython(httpdef, props)
        script_exe.pre_request_script()
        self.assertEquals({"ram": "ranga"}, httpdef.headers)
        self.assertEquals({
            "new": "value",
            "ram": "raju"
        }, script_exe.client.properties)

    def test_math_n_headers(self):
        resp = self.get_script_exe("""
class SampleTestCase(unittest.TestCase):
    def test_math(self):
        self.assertEquals(4 , math.pow(2,2))

    def test_headers(self):
        self.assertEquals("sample_value", client.response.headers.get("sample_header"))

    def test_date(self):
        datetime.datetime.now()

    def test_hash(self):
        hashobj = hashlib.sha512()
        hashobj.update(b'ram')
        self.assertEquals("92f35115cca41c3270b11813164b0845108686761d73b3e6e4e95ae8380fbdd92c1b9d6ff0e6181214486e9eb7ccdd779ffe1b04b161e510c7d8e7da715eb0ae", 
        hashobj.hexdigest())

""")
        self.assertEqual(
            {
                'compiled':
                True,
                'error':
                '',
                'properties': {},
                'stdout':
                '',
                'tests': [{
                    'name': 'test_date (test_script.SampleTestCase)',
                    'success': True,
                    'result': None,
                    'error': None
                }, {
                    'name': 'test_hash (test_script.SampleTestCase)',
                    'success': True,
                    'result': None,
                    'error': None
                }, {
                    'name': 'test_headers (test_script.SampleTestCase)',
                    'success': True,
                    'result': None,
                    'error': None
                }, {
                    'name': 'test_math (test_script.SampleTestCase)',
                    'success': True,
                    'result': None,
                    'error': None
                }]
            }, resp.as_json())

    def test_assertion_failure(self):
        resp = self.get_script_exe("""
class SampleTestCase(unittest.TestCase):
    def test_status_code(self):
        self.assertEquals(401 , client.response.status_code)
""")
        self.assertEqual(
            {
                'stdout':
                '',
                'error':
                '',
                'properties': {},
                'tests': [{
                    'name':
                    'test_status_code (test_script.SampleTestCase)',
                    'success':
                    False,
                    'result':
                    None,
                    'error':
                    'Traceback (most recent call last):\n  File "test_script.py", line 4, in test_status_code\nAssertionError: 401 != 200\n'
                }],
                'compiled':
                True
            }, resp.as_json())

    def test_exception(self):
        resp = self.get_script_exe("""
class SampleTestCase(unittest.TestCase):
    def test_raise(self):
        raise Exception()
""")
        self.assertEqual(
            {
                'compiled':
                True,
                'error':
                '',
                'properties': {},
                'stdout':
                '',
                'tests': [{
                    'error':
                    'Traceback (most recent call last):\n'
                    '  File "test_script.py", line 4, in test_raise\n'
                    'Exception\n',
                    'name':
                    'test_raise (test_script.SampleTestCase)',
                    'result':
                    None,
                    'success':
                    False
                }]
            }, resp.as_json())
