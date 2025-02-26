import unittest
import os
import base64
import shutil
from dotextensions.server.handlers.fs_handlers import (
    CopyHandler, RenameHandler, DeleteHandler, WriteHandler, ReadHandler,
    CreateDirectoryHandler, ReadDirectoryHandler, FileStatHandler
)
from dotextensions.server.models import Command, Result
import tempfile

class TestFsHandlers(unittest.TestCase):
    
    def setUp(self):
        # create a temp directory
        self.temp_dir = tempfile.TemporaryDirectory(dir="/tmp")
        return super().setUp()
    
    def tearDown(self):
        self.temp_dir.cleanup()
        return super().tearDown()
    
    def test_copy_handler(self):
        handler = CopyHandler()
        source = os.path.join(self.temp_dir.name, "source.txt")
        destination = os.path.join(self.temp_dir.name, "destination.txt")
        with open(source, "w") as f:
            f.write("Hello World")
        command = Command(id=1, method=handler.get_method(), params={"source": source, "destination": destination})
        result = handler.run(command)
        self.assertTrue(result.result['result']["success"])
        self.assertTrue(os.path.exists(destination))
        with open(destination, "r") as f:
            self.assertEqual(f.read(), "Hello World")
    
    def test_copy_handler_error(self):
        handler = CopyHandler()
        source = os.path.join(self.temp_dir.name, "source.txt")
        destination = os.path.join(self.temp_dir.name, "destination.txt")
        command = Command(id=1, method=handler.get_method(), params={"source": source, "destination": destination})
        result = handler.run(command)
        self.assertTrue(result.result["error"])
        self.assertEqual(result.result["error_message"], "FileNotFound")

    def test_rename_handler(self):
        handler = RenameHandler()
        source = os.path.join(self.temp_dir.name, "source1.txt")
        destination = os.path.join(self.temp_dir.name, "destination1.txt")
        with open(source, "w") as f:
            f.write("Hello World")
        command = Command(id=1, method=handler.get_method(), params={"old": source, "new": destination})
        result = handler.run(command)
        self.assertTrue(result.result['result']["success"])
        self.assertFalse(os.path.exists(source))
        self.assertTrue(os.path.exists(destination))
        with open(destination, "r") as f:
            self.assertEqual(f.read(), "Hello World")
        
    
    def test_rename_handler_error(self):
        handler = RenameHandler()
        source = os.path.join(self.temp_dir.name, "source_r.txt")
        destination = os.path.join(self.temp_dir.name, "destination_r.txt")
        command = Command(id=1, method=handler.get_method(), params={"old": source, "new": destination})
        result = handler.run(command)
        self.assertTrue(result.result["error"])
        self.assertEqual(result.result["error_message"], "FileNotFound")

    def test_delete_handler(self):
        handler = DeleteHandler()
        source = os.path.join(self.temp_dir.name, "source_d1.txt")
        with open(source, "w") as f:
            f.write("Hello World")
        command = Command(id=1, method=handler.get_method(), params={"source": source})
        result = handler.run(command)
        self.assertTrue(result.result['result']["success"])
        self.assertFalse(os.path.exists(source))
    
    def test_delete_handler_error(self):
        handler = DeleteHandler()
        source = os.path.join(self.temp_dir.name, "source_d2.txt")
        command = Command(id=1, method=handler.get_method(), params={"source": source})
        result = handler.run(command)
        self.assertTrue(result.result["error"])
        self.assertEqual(result.result["error_message"], "FileNotFound")
    
    def test_write_handler(self):
        handler = WriteHandler()
        source = os.path.join(self.temp_dir.name, "source_w1.txt")
        content = "Hello World"
        b64_content = base64.b64encode("Hello World".encode()).decode()
        command = Command(id=1, method=handler.get_method(), params={"source": source, "content": b64_content})
        result = handler.run(command)
        self.assertTrue(result.result['result']["success"])
        self.assertTrue(os.path.exists(source))
        with open(source, "r") as f:
            self.assertEqual(f.read(), content)

    def test_write_handler_error(self):
        handler = WriteHandler()
        source = os.path.join(self.temp_dir.name, "source_w2.txt")
        content = "Hello World"
        b64_content = base64.b64encode("Hello World".encode()).decode()
        command = Command(id=1, method=handler.get_method(), params={"source": source})
        result = handler.run(command)
        self.assertTrue(result.result["error"])
        self.assertEqual(result.result["error_message"], "source and content are required")


    def test_read_handler(self):
        handler = ReadHandler()
        source = os.path.join(self.temp_dir.name, "source_r1.txt")
        with open(source, "w") as f:
            f.write("Hello World")
        command = Command(id=1, method=handler.get_method(), params={"source": source})
        result = handler.run(command)
        self.assertEqual(base64.b64decode(result.result['result']["content"]).decode(), "Hello World")


    def test_read_handler_error(self):
        handler = ReadHandler()
        source = os.path.join(self.temp_dir.name, "source_r2.txt")
        command = Command(id=1, method=handler.get_method(), params={"source": source})
        result = handler.run(command)
        self.assertTrue(result.result["error"])
        self.assertEqual(result.result["error_message"], "FileNotFound")

    def test_create_directory_handler(self):
        handler = CreateDirectoryHandler()
        source = os.path.join(self.temp_dir.name, "source_d1")
        command = Command(id=1, method=handler.get_method(), params={"source": source})
        result = handler.run(command)
        self.assertTrue(result.result['result']["success"])
        self.assertTrue(os.path.exists(source))
    
    def test_create_directory_handler_error(self):
        handler = CreateDirectoryHandler()
        source = os.path.join(self.temp_dir.name, "source_d2")
        command = Command(id=1, method=handler.get_method(), params={})
        result = handler.run(command)
        self.assertTrue(result.result["error"])
        self.assertEqual(result.result["error_message"], "source is required")
    
    def test_read_directory_handler(self):
        handler = ReadDirectoryHandler()
        source = os.path.join(self.temp_dir.name, "source_d1")
        os.mkdir(source)
        command = Command(id=1, method=handler.get_method(), params={"source": source})
        result = handler.run(command)
        self.assertEqual(result.result['result']["files"], [])
    
    def test_read_directory_handler_error(self):
        handler = ReadDirectoryHandler()
        source = os.path.join(self.temp_dir.name, "source_d2")
        command = Command(id=1, method=handler.get_method(), params={})
        result = handler.run(command)
        self.assertTrue(result.result["error"])
        self.assertEqual(result.result["error_message"], "source is required")

if __name__ == "__main__":
    unittest.main()