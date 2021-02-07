import argparse
import logging

from . import CurlCompiler, RequestCompiler, Config, eprint
from .exceptions import DotHttpException

logger = logging.getLogger('dothttp')


def apply(args: Config):
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    setup_logging(args)
    logger.info(f'command line arguments are {args}')
    comp_clss: CurlCompiler | RequestCompiler = CurlCompiler if args.curl else RequestCompiler
    try:
        comp_clss(args).run()
    except DotHttpException as dotthtppexc:
        logger.error(f'dothttp exception happened {dotthtppexc}', exc_info=True)
        eprint(dotthtppexc.message)
    except Exception as exc:
        logger.error(f'unknown error happened {exc}', exc_info=True)
        eprint(f'unknown exception occurred with message {exc}')


def setup_logging(args):
    level = logging.DEBUG if args.debug else logging.CRITICAL
    # TODO need to add seperate levels. verbose ...
    logging.getLogger('dothttp').setLevel(level)
    logging.getLogger('request').setLevel(level)
    logging.getLogger('curl').setLevel(level)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Make http requests', prog="dothttp")
    parser.add_argument('--curl', help='generates curl script',
                        action='store_const', const=True)
    parser.add_argument('--property-file', '-p', help='property file')
    parser.add_argument('--no-cookie', '-nc', help='cookie storage is disabled', action='store_const', const=True)
    parser.add_argument('--env', '-e',
                        help='environment to select in property file. properties will be enabled on FIFO',
                        nargs='+', default=['*'])
    parser.add_argument(
        '--debug', '-d', help='debug will enable logs and exceptions', action='store_const', const=True)
    # TODO add conflits with debug for info
    parser.add_argument(
        '--info', '-i', help='more information', action='store_const', const=True)
    parser.add_argument(
        '--property', help='list of property\'s', nargs='+', default=[])
    parser.add_argument('file', help='http file')

    args = parser.parse_args()
    config = Config(curl=args.curl, property_file=args.property_file, env=args.env, debug=args.debug, file=args.file,
                    info=args.info, propertys=args.property, no_cookie=args.no_cookie)
    apply(config)
