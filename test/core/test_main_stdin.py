import json
import os
import subprocess
import sys
import tempfile
from unittest import TestCase, mock

from dothttp.__main__ import main

repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def run_dothttp(args, http_content, cwd=repo_root):
    # PYTHONPATH ensures the package resolves even when `cwd` isn't the repo
    # root (e.g. testing property-file auto-discovery from another directory)
    # and dothttp isn't pip-installed in the current environment.
    env = {**os.environ, "PYTHONPATH": repo_root}
    return subprocess.run(
        [sys.executable, "-m", "dothttp", *args],
        input=http_content,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        timeout=30,
    )


# integration tests -- actually invoke `python -m dothttp` as a subprocess,
# piping http content on stdin, against the local httpbin (test/conftest.py)
class MainStdinIntegrationTest(TestCase):
    def test_explicit_dash_reads_stdin_and_prints_response_on_stdout(self):
        result = run_dothttp(["-"], 'GET "http://localhost:8000/get"')
        self.assertEqual(0, result.returncode, result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual("http://localhost:8000/get", response["url"])
        self.assertNotIn("------------", result.stdout)

    def test_omitted_file_reads_stdin_and_prints_response_on_stdout(self):
        result = run_dothttp([], 'GET "http://localhost:8000/get"')
        self.assertEqual(0, result.returncode, result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual("http://localhost:8000/get", response["url"])

    def test_curl_flag_with_stdin(self):
        result = run_dothttp(
            ["-", "--curl"],
            'GET "http://localhost:8000/get"\nheader("X-Test", "1")',
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("http://localhost:8000/get", result.stdout)
        self.assertIn("X-Test: 1", result.stdout)

    def test_format_flag_with_stdin_prints_to_stdout_not_file(self):
        result = run_dothttp(
            ["-", "--format", "--experimental"], 'GET "http://localhost:8000/get"'
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('GET "http://localhost:8000/get"', result.stdout)

    def test_target_flag_selects_correct_def_with_stdin(self):
        content = (
            'GET "http://localhost:8000/get"\n\n\n'
            'POST "http://localhost:8000/post"\n'
        )
        result = run_dothttp(["-", "--target", "2"], content)
        self.assertEqual(0, result.returncode, result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual("http://localhost:8000/post", response["url"])

    def test_command_line_property_substitution_with_stdin(self):
        content = 'GET "http://localhost:8000/get?key={{myprop}}"'
        result = run_dothttp(["-", "--property", "myprop=myvalue"], content)
        self.assertEqual(0, result.returncode, result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual("myvalue", response["args"]["key"])

    def test_property_file_auto_discovered_from_cwd_with_stdin(self):
        # `args.file` is set to a placeholder path under cwd when input
        # comes from stdin, specifically so property-file auto-discovery
        # (.dothttp.json in the current directory) still works.
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, ".dothttp.json"), "w") as f:
                json.dump({"*": {"myprop": "fromfile"}}, f)
            content = 'GET "http://localhost:8000/get?key={{myprop}}"'
            result = run_dothttp(["-"], content, cwd=tmp_dir)
            self.assertEqual(0, result.returncode, result.stderr)
            response = json.loads(result.stdout)
            self.assertEqual("fromfile", response["args"]["key"])

    def test_real_file_argument_still_works(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = f"{dir_path}/requests/pass.http"
        result = subprocess.run(
            [sys.executable, "-m", "dothttp", file_path],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=30,
        )
        self.assertEqual(0, result.returncode, result.stderr)


# unit test for the isatty guard -- calling main() directly lets us
# monkeypatch sys.stdin.isatty() without needing a real pty.
class MainNoInputGuardTest(TestCase):
    def test_errors_when_no_file_and_no_piped_stdin(self):
        with mock.patch.object(sys, "argv", ["dothttp"]), mock.patch.object(
            sys.stdin, "isatty", return_value=True
        ):
            with self.assertRaises(SystemExit):
                main()
