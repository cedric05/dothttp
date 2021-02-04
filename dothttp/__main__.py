import argparse

from . import RequestCompiler, CurlCompiler


def apply(args):
    comp_clss = CurlCompiler if args.curl else RequestCompiler
    comp_clss(args).run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Make http requests', prog="dothttp")
    parser.add_argument('--curl', help='generates curl script', action='store_const', const=True)
    parser.add_argument('--property-file', '-p', help='property file')
    parser.add_argument('--env', '-e', help='environment to select in property file')
    parser.add_argument('file', help='http file')

    args = parser.parse_args()
    apply(args)
