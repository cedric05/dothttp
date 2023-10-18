import os
import tempfile
import unittest

from dothttp import dothttp_model
from dothttp.exceptions import HttpFileException, HttpFileSyntaxException
from dothttp.parse_models import MultidefHttp, ImportStmt, FileName
from dothttp import BaseModelProcessor, PropertyProvider


class TestBaseModelProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = BaseModelProcessor

    def test_load_imports_with_no_imports(self):
        model = MultidefHttp(allhttps=[], import_list=[])
        filename = "test.http"
        property_util = PropertyProvider()
        import_list = []
        self.processor._load_imports(model, filename, property_util, import_list)
        self.assertEqual(len(import_list), 0)

    def test_load_imports_with_absolute_import_file(self):
        model = MultidefHttp(allhttps=[], import_list=[])
        filename = "test.dothttp"
        property_util = PropertyProvider()
        import_list = []
        import_file = os.path.join(tempfile.gettempdir(), "test_import.http")
        with open(import_file, "w") as f:
            f.write("GET https://httpbin.org/get")
        model.import_list = ImportStmt()
        model.import_list.filename = [FileName(import_file)]
        self.processor._load_imports(model, filename, property_util, import_list)
        self.assertEqual(len(import_list), 1)
        self.assertEqual(import_list[0].urlwrap.url, "https://httpbin.org/get")

    def test_load_imports_with_relative_import_file(self):
        model = MultidefHttp(allhttps=[], import_list=[])
        model.import_list = ImportStmt()
        model.import_list.filename = [FileName("./test_import.http")]
        filename = os.path.join(tempfile.gettempdir(), "test.thttp")
        property_util = PropertyProvider()
        import_list = []
        import_file = os.path.join(tempfile.gettempdir(), "test_import.http")
        with open(import_file, "w") as f:
            f.write("GET https://httpbin.org/get")
        self.processor._load_imports(model, filename, property_util, import_list)
        self.assertEqual(len(import_list), 1)
        self.assertEqual(import_list[0].urlwrap.url, "https://httpbin.org/get")


    def test_load_imports_with_nonexistent_import_file(self):
        model = MultidefHttp(allhttps=[], import_list=[])
        filename = "test.dothttp"
        property_util = PropertyProvider()
        import_list = []
        import_file = "nonexistent.http"
        model.import_list = ImportStmt()
        model.import_list.filename = [FileName(import_file)]
        with self.assertRaises(HttpFileException):
            self.processor._load_imports(model, filename, property_util, import_list)

    def test_load_imports_with_nonexistent_import_file_with_http_extension(self):
        model = MultidefHttp(allhttps=[], import_list=[])
        filename = "test.dothttp"
        property_util = PropertyProvider()
        import_list = []
        import_file = "nonexistent"
        model.import_list = ImportStmt()
        model.import_list.filename = [FileName(import_file)]

        with self.assertRaises(HttpFileException):
            self.processor._load_imports(model, filename, property_util, import_list)

    def test_load_imports_with_syntax_error_in_import_file(self):
        property_util = PropertyProvider()
        import_list = []
        import_file = os.path.join(tempfile.gettempdir(), "test_import.http")
        with open(import_file, "w") as f:
            f.write("INVALID SYNTAX")
        model = dothttp_model.model_from_str(f"import '{import_file}'; GET 'https://httpbin.org/get'")
        with self.assertRaises(HttpFileSyntaxException):
            self.processor._load_imports(model, import_file, property_util, import_list)

    def test_load_imports_with_nested_imports(self):
        model = MultidefHttp(allhttps=[], import_list=[])
        model.import_list = ImportStmt()
        property_util = PropertyProvider()
        import_list = []
        filename = os.path.join(tempfile.gettempdir(), "test.dothttp")
        model.import_list.filename = [FileName(filename)]
        import_file1 = os.path.join(tempfile.gettempdir(), "test_import1.http")
        import_file2 = os.path.join(tempfile.gettempdir(), "test_import2.http")
        with open(import_file1, "w") as f:
            f.write(f"import '{import_file2}'; GET 'https://httpbin.org/2' ")
        with open(import_file2, "w") as f:
            f.write("GET https://httpbin.org/3")
        with open(filename, "w") as f:
            f.write(f"import '{import_file1}'; GET 'https://httpbin.org/1' ")
        self.processor._load_imports(model, filename, property_util, import_list)
        self.assertEqual(len(import_list), 3)
        self.assertEqual(import_list[0].urlwrap.url, "https://httpbin.org/1")
        self.assertEqual(import_list[1].urlwrap.url, "https://httpbin.org/2")
        self.assertEqual(import_list[2].urlwrap.url, "https://httpbin.org/3")
