import importlib.metadata 
module_name = "dothttp-req"
try:
    __version__ = importlib.metadata.version(module_name)
except:
    # to support testing
    __version__ = "0.0.0"
