

import base64
import os
from dotextensions.server.models import BaseHandler, Result
import shutil


class CopyHandler(BaseHandler):
    def get_method(self):
        return "/fs/copy"

    def run(self, command):
        source = command.params.get("source")
        destination = command.params.get("destination")
        if not source or not destination:
            return Result.to_error(command, "source and destination are required")
        try:
            shutil.copy2(source, destination)
        except FileNotFoundError:
            return Result.to_error(command, "FileNotFound")
        except PermissionError:
            return Result.to_error(command, "PermissionError")
        except Exception as e:
            return Result.to_error(command, str(e))
        return Result.get_result(command, {"result": {"operation": "copy", "success": True}})


class RenameHandler(BaseHandler):
    def get_method(self):
        return "/fs/rename"

    def run(self, command):
        source = command.params.get("old")
        destination = command.params.get("new")
        if not source or not destination:
            return Result.to_error(command, "source and destination are required")
        try:
            shutil.move(source, destination)
        except FileNotFoundError:
            return Result.to_error(command, "FileNotFound")
        except Exception as e:
            return Result.to_error(command, str(e))
        return Result.get_result(command, {"result": {"operation": "rename", "success": True}})


class DeleteHandler(BaseHandler):
    def get_method(self):
        return "/fs/delete"

    def run(self, command):
        source = command.params.get("source")
        if not source:
            return Result.to_error(command, "source is required")
        try:
            if os.path.isfile(source):
                os.remove(source)
            else:
                shutil.rmtree(source)
        except FileNotFoundError:
            return Result.to_error(command, "FileNotFound")
        except PermissionError:
            return Result.to_error(command, "PermissionError")
        except Exception as e:
            return Result.to_error(command, str(e))
        return Result.get_result(command, {"result": {"operation": "delete", "success": True}})
    

class WriteHandler(BaseHandler):
    def get_method(self):
        return "/fs/write"

    def run(self, command):
        source = command.params.get("source")
        content = command.params.get("content")
        if not source:
            return Result.to_error(command, "source and content are required")
        if not content:
            content = ""
        try:
            with open(source, "wb") as f:
                f.write(base64.b64decode(content))
        except FileNotFoundError:
            return Result.to_error(command, "FileNotFound")
        except PermissionError:
            return Result.to_error(command, "PermissionError")
        except IsADirectoryError:
            return Result.to_error(command, "IsADirectoryError")
        except IsADirectoryError:
            return Result.to_error(command, "IsADirectoryError")
        except Exception as e:
            return Result.to_error(command, str(e))
        return Result.get_result(command, {"result": {"operation": "write", "success": True}})
    
class ReadHandler(BaseHandler):
    def get_method(self):
        return "/fs/read"

    def run(self, command):
        source = command.params.get("source")
        if not source:
            return Result.to_error(command, "source is required")
        try:
            with open(source, "rb") as f:
                content = base64.b64encode(f.read()).decode()
        except FileNotFoundError:
            return Result.to_error(command, "FileNotFound")
        except Exception as e:
            return Result.to_error(command, str(e))
        return Result.get_result(command, {"result": {"operation": "read", "content": content}})

class CreateDirectoryHandler(BaseHandler):
    def get_method(self):
        return "/fs/create-directory"

    def run(self, command):
        source = command.params.get("source")
        if not source:
            return Result.to_error(command, "source is required")
        try:
            os.mkdir(source)
        except FileExistsError:
            return Result.to_error(command, "FileExists")
        except FileNotFoundError:
            return Result.to_error(command, "FileNotFound")
        except PermissionError:
            return Result.to_error(command, "PermissionError")
        except Exception as e:
            return Result.to_error(command, str(e))
        return Result.get_result(command, {"result": {"operation": "create-directory", "success": True}})

class ReadDirectoryHandler(BaseHandler):
    def get_method(self):
        return "/fs/read-directory"

    def run(self, command):
        source = command.params.get("source")
        if not source:
            return Result.to_error(command, "source is required")
        try:
            return_data = []
            with os.scandir(source) as it:
                for entry in it:
                    if entry.is_file():
                        return_data.append([entry.name, "file"])
                    elif entry.is_dir():
                        return_data.append([entry.name, "directory"])
                    elif entry.is_symlink():
                        return_data.append([entry.name, "symlink"])
        except FileNotFoundError:
            return Result.to_error(command, "FileNotFound")
        except Exception as e:
            return Result.to_error(command, str(e))
        return Result.get_result(command, {"result": {"operation": "read-directory", "files": return_data}})
    

class FileStatHandler(BaseHandler):
    def get_method(self):
        return "/fs/stat"
    
    def run(self, command):
        source = command.params.get("source")
        if not source:
            return Result.to_error(command, "source is required")
        try:
            stat = os.stat(source)
        except FileNotFoundError:
            return Result.to_error(command, "FileNotFound")
        except Exception as e:
            return Result.to_error(command, str(e))
        return Result.get_result(command, {"result": {"operation": "stat", "stat": stat}})