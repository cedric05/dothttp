import argparse
import asyncio
import logging
import sys

from dothttp.__version__ import __version__
from dothttp.utils.log_utils import setup_logging as root_logging_setup

from .server import AsyncCmdServer, CmdServer, HttpServer


def setup_logging(level):
    root_logging_setup(level)
    logging.getLogger("cmd-server").setLevel(level)
    logging.getLogger("handler").setLevel(level)
    logging.root.setLevel(level)


def start_server(server_type, port=5000):
    setup_logging(logging.DEBUG)
    if server_type == "http":
        HttpServer(port).run_forever()
    elif server_type == "version":
        print(__version__)
    elif server_type == "async":
        print("async")
        asyncio.run(AsyncCmdServer().run_forever())
    elif server_type == "cmd":
        CmdServer().run_forever()
    else:
        sys.exit(1)
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Run the server.")
    parser.add_argument(
        "--server_type",
        choices=["http", "version", "async", "cmd"],
        help="Type of server to run",
        default="cmd",
    )
    parser.add_argument(
        "--port",
        nargs="?",
        type=int,
        default=5000,
        help="Port number (only for http server)",
    )
    args = parser.parse_args()
    start_server(args.server_type, args.port)


if __name__ == "__main__":
    main()
