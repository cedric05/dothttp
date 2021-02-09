import argparse
import logging
import sys

from . import CurlCompiler, RequestCompiler, HttpFileFormatter, Config, eprint
from .exceptions import DotHttpException

logger = logging.getLogger('dothttp')


def apply(args: Config):
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    setup_logging(args)
    logger.info(f'command line arguments are {args}')
    if args.format:
        comp_class = HttpFileFormatter
    elif args.curl:
        comp_class = CurlCompiler
    else:
        comp_class = RequestCompiler
    try:
        comp_class(args).run()
    except DotHttpException as dotthtppexc:
        logger.error(f'dothttp exception happened {dotthtppexc}', exc_info=True)
        eprint(dotthtppexc.message)
    except Exception as exc:
        logger.error(f'unknown error happened {exc}', exc_info=True)
        eprint(f'unknown exception occurred with message {exc}')


def setup_logging(args):
    level = logging.DEBUG if args.debug else logging.CRITICAL
    logging.getLogger('dothttp').setLevel(level)
    logging.getLogger('request').setLevel(level)
    logging.getLogger('curl').setLevel(level)


def main():
    parser = argparse.ArgumentParser(
        description='http requests for humans', prog="dothttp")
    general_group = parser.add_argument_group('general')
    general_group.add_argument('--curl', help='generates curl script',
                               action='store_const', const=True)
    property_group = parser.add_argument_group('property')
    property_group.add_argument('--property-file', '-p', help='property file')
    general_group.add_argument('--no-cookie', '-nc', help='cookie storage is disabled', action='store_const',
                               const=True)
    property_group.add_argument('--env', '-e',
                                help='environment to select in property file. properties will be enabled on FIFO',
                                nargs='+', default=['*'])
    general_group.add_argument(
        '--debug', '-d', help='debug will enable logs and exceptions', action='store_const', const=True)
    general_group.add_argument(
        '--info', '-i', help='more information', action='store_const', const=True)
    fmt_group = parser.add_argument_group('format')
    fmt_group.add_argument(
        '--format', '-fmt', help='formatter', action='store_const', const=True)
    fmt_group.add_argument(
        '--stdout', help='print to commandline', action='store_const', const=True)
    property_group.add_argument(
        '--property', help='list of property\'s', nargs='+', default=[])
    general_group.add_argument('file', help='http file')
    args = parser.parse_args()
    if args.debug and args.info:
        eprint("info and debug are conflicting options, use debug for more information")
        sys.exit(1)
    for one_prop in args.property:
        if '=' not in one_prop:
            # FUTURE,
            # this can be done better by adding validation in add_argument.
            eprint(f"command line property: `{one_prop}` is invalid, expected prop=val")
            sys.exit(1)
    config = Config(curl=args.curl, property_file=args.property_file, env=args.env, debug=args.debug, file=args.file,
                    info=args.info, properties=args.property, no_cookie=args.no_cookie,
                    format=args.format, stdout=args.stdout)
    apply(config)


if __name__ == "__main__":
    main()
