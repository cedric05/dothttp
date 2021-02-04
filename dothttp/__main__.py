import argparse
import logging
import traceback 

from . import CurlCompiler, RequestCompiler, RequestBase
from .exceptions import DotHttpException
import sys


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


logger = logging.getLogger('dothttp')


def apply(args):
    logger.info(f'command line arguments are {args}')
    comp_clss: RequestBase = CurlCompiler if args.curl else RequestCompiler
    try:
        comp_clss(args).run()
    except DotHttpException as dotthtppexc:
        logger.error(f'dothttp exception happened {dotthtppexc}')
        eprint(dotthtppexc.message)
    except Exception as exc:
        # TODO remove below comments
        # traceback.print_exc() 
        # print(exc)
        logger.error(f'unknown error happened {exc}')
        eprint(f'unknown exception occurred with message {exc}')


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
    if args.debug:
        # TODO need to add seperate levels. verbose ...
        logging.getLogger('dothttp').setLevel(logging.DEBUG)
        logging.getLogger('request').setLevel(logging.DEBUG)
        logging.getLogger('curl').setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.CRITICAL)
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    apply(args)
