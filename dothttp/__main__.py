import argparse
import logging
import sys

from requests.exceptions import RequestException

from dothttp.log_utils import setup_logging
from .exceptions import DotHttpException
from .request_base import CurlCompiler, RequestCompiler, HttpFileFormatter, Config, eprint

logger = logging.getLogger('dothttp')


def apply(args: Config):
    setup_logging(logging.DEBUG if args.debug else logging.CRITICAL)
    logger.info(f'command line arguments are {args}')
    if args.format:
        if args.experimental:
            comp_class = HttpFileFormatter
        else:
            eprint("http formatter is still in experimental phase. enable experimental flag to use it (--experimental)")
            sys.exit(1)
    elif args.curl:
        comp_class = CurlCompiler
    else:
        comp_class = RequestCompiler
    try:
        comp_class(args).run()
    except DotHttpException as dotthtppexc:
        logger.error(f'dothttp exception happened {dotthtppexc}', exc_info=True)
        eprint(dotthtppexc.message)
    except RequestException as exc:
        logger.error(f'exception from requests {exc}', exc_info=True)
        eprint(exc)
    except Exception as exc:
        logger.error(f'unknown error happened {exc}', exc_info=True)
        eprint(f'unknown exception occurred with message {exc}')


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
        '--format', '-fmt', help='format http file', action='store_const', const=True)
    property_group.add_argument(
        '--experimental', '--b', help='enable experimental', action='store_const', const=True)
    fmt_group.add_argument(
        '--stdout', help='print to commandline', action='store_const', const=True)
    property_group.add_argument(
        '--property', help='list of property\'s', nargs='+', default=[])
    general_group.add_argument('file', help='http file')
    general_group.add_argument('--target', '-t', help='targets a particular http definition', type=str)
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
                    target=args.target,
                    format=args.format, stdout=args.stdout, experimental=args.experimental)
    apply(config)


if __name__ == "__main__":
    main()
