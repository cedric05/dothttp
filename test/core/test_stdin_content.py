import io
import os
import tempfile
from contextlib import redirect_stdout

from test import TestBase

# these exercise `Config.content`, the code path the CLI now uses when
# http content is piped via stdin instead of read from a file on disk.
# requests are pointed at the local httpbin (see test/conftest.py) so
# no external network access is required.


class ContentBasedInputTest(TestBase):
    def test_request_compiler_builds_request_from_content(self):
        req = self.get_request_comp(
            "/nonexistent/-", content='GET "http://localhost:8000/get"'
        ).get_request()
        self.assertEqual("http://localhost:8000/get", req.url)
        self.assertEqual("GET", req.method)

    def test_curl_compiler_builds_curl_from_content(self):
        content = 'GET "http://localhost:8000/get"\nheader("X-Test", "1")'
        comp = self.get_req_comp("/nonexistent/-", curl=True, content=content)
        curl_output = comp.get_curl_output()
        self.assertIn("http://localhost:8000/get", curl_output)
        self.assertIn("X-Test: 1", curl_output)

    def test_format_forces_stdout_when_content_provided(self):
        # stdout=False and a file path that doesn't (and can't) exist:
        # content-based input must never attempt to write to disk.
        comp = self.get_req_comp(
            "/nonexistent/should-not-be-written.http",
            format=True,
            stdout=False,
            content='GET "http://localhost:8000/get"',
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            comp.run()
        self.assertIn("http://localhost:8000/get", buf.getvalue())

    def test_no_script_result_noise_without_script(self):
        comp = self.get_req_comp(
            "/nonexistent/-", content='GET "http://localhost:8000/get"'
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            comp.run()
        self.assertNotIn("------------", buf.getvalue())

    def test_script_result_still_printed_when_script_present(self):
        content = (
            'GET "http://localhost:8000/get"\n'
            "> {%\n\n"
            "class SampleTest(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertEqual(200, client.response.status_code)\n\n"
            "%} python\n"
        )
        comp = self.get_req_comp("/nonexistent/-", content=content)
        buf = io.StringIO()
        with redirect_stdout(buf):
            comp.run()
        output = buf.getvalue()
        self.assertIn("------------", output)
        self.assertIn("##TESTS", output)

    def test_target_selects_correct_def_among_multiple_in_content(self):
        content = (
            'GET "http://localhost:8000/get"\n\n\n'
            'POST "http://localhost:8000/post"\n'
        )
        req = self.get_request_comp(
            "/nonexistent/-", content=content, target="2"
        ).get_request()
        self.assertEqual("http://localhost:8000/post", req.url)
        self.assertEqual("POST", req.method)

    def test_command_line_property_substitution_with_content(self):
        content = 'GET "http://localhost:8000/get?key={{myprop}}"'
        comp = self.get_req_comp(
            "/nonexistent/-", content=content, properties=["myprop=myvalue"]
        )
        req = comp.get_request()
        self.assertEqual("http://localhost:8000/get?key=myvalue", req.url)

    def test_output_directive_writes_to_file_even_with_stdin_content(self):
        # an explicit `>> file` directive in the http content should still
        # win over stdout, even though the input itself came from stdin.
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = os.path.join(tmp_dir, "out.txt")
            content = f'GET "http://localhost:8000/get"\n>> "{out_file}"'
            comp = self.get_req_comp("/nonexistent/-", content=content)
            buf = io.StringIO()
            with redirect_stdout(buf):
                comp.run()
            self.assertEqual("", buf.getvalue())
            with open(out_file) as f:
                self.assertIn("http://localhost:8000/get", f.read())
