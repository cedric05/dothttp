import logging
import sys

from dothttp.log_utils import setup_logging as root_logging_setup
from dothttp.__version__ import __version__
from .server import CmdServer, HttpServer


def setup_logging(level):
    root_logging_setup(level)
    logging.getLogger("cmd-server").setLevel(level)
    logging.getLogger('handler').setLevel(level)
    logging.root.setLevel(level)


def main():
    setup_logging(logging.DEBUG)
    if len(sys.argv) == 2:
        type_of_server = sys.argv[1]
    else:
        type_of_server = "cmd"
    if type_of_server == "cmd":
        CmdServer().run_forever()
    elif type_of_server == "http":
        port = 5000
        if len(sys.argv) == 3:
            try:
                port = int(sys.argv[3])
            except ValueError:
                pass
        HttpServer(port).run_forever()
    elif type_of_server == "version":
        print(__version__)
    else:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
