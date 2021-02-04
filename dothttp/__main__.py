import argparse

from . import RequestCompiler, CurlCompiler
from .exceptions import DotHttpException


def apply(args):
    comp_clss = CurlCompiler if args.curl else RequestCompiler
    try:
        comp_clss(args).run()
    except DotHttpException as dotthtppexc:
        # TODO fix message statement
        # message should come to stderr, not stdout
        print(dotthtppexc.message)
    except Exception as exc:
        # TODO fix message statement
        # message should come to stderr, not stdout
        # TODO enable logging, if debug enabled, we should mention each step
        print(f'unknown exception occurred with message {exc.message}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Make http requests', prog="dothttp")
    parser.add_argument('--curl', help='generates curl script',
                        action='store_const', const=True)
    parser.add_argument('--property-file', '-p', help='property file')
    parser.add_argument('--env', '-e', help='environment to select in property file. properties will be enabled on FIFO',
                        nargs='+', default=['*'])
    parser.add_argument(
        '--debug', '-d', help='debug will enable logs and exceptions', action='store_const', const=True)
    parser.add_argument('file', help='http file')

    args = parser.parse_args()
    apply(args)
