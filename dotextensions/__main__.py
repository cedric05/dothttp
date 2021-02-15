import logging
import sys

from dotextensions.server import CmdServer, HttpServer

logger = logging.getLogger("cmd-server")


def setup_logging(level):
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    logging.getLogger('dothttp').setLevel(level)
    logging.getLogger('request').setLevel(level)
    logging.getLogger('curl').setLevel(level)
    logging.getLogger("cmd-server").setLevel(level)
    logging.getLogger('handler').setLevel(level)
    logging.root.setLevel(level)


setup_logging(logging.DEBUG)


def run(command):
    return {}


def main():
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
    sys.exit(1)


if __name__ == "__main__":
    main()
