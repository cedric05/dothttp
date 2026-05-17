import argparse
import atexit
import logging
import sys

from requests.exceptions import RequestException

from .exceptions import DotHttpException
from .parse.request_base import (
    Config,
    CurlCompiler,
    HttpFileFormatter,
    RequestCompiler,
    eprint,
)
from .plugin_system import cleanup_plugins, ensure_integrated
from .utils.log_utils import setup_logging

logger = logging.getLogger("dothttp")

# Ensure plugins are auto-integrated
ensure_integrated()

# Register cleanup handler
atexit.register(cleanup_plugins)


def apply(args: Config):
    setup_logging(logging.DEBUG if args.debug else logging.CRITICAL)
    logger.info(f"command line arguments are {args}")
    if args.format:
        if args.experimental:
            comp_class = HttpFileFormatter
        else:
            eprint(
                "http formatter is still in experimental phase. enable experimental flag to use it (--experimental)"
            )
            sys.exit(1)
    elif args.curl:
        comp_class = CurlCompiler
    else:
        comp_class = RequestCompiler
    try:
        comp_class(args).run()
    except DotHttpException as dotthtppexc:
        logger.error(f"dothttp exception happened {dotthtppexc}", exc_info=True)
        eprint(dotthtppexc.message)
    except RequestException as exc:
        logger.error(f"exception from requests {exc}", exc_info=True)
        eprint(exc)
    except Exception as exc:
        logger.error(f"unknown error happened {exc}", exc_info=True)
        eprint(f"unknown exception occurred with message {exc}")


def main():
    parser = argparse.ArgumentParser(
        description="http requests for humans", prog="dothttp"
    )

    # Add subparsers for plugin commands
    subparsers = parser.add_subparsers(dest='command', help='commands')

    # Plugin command
    plugin_parser = subparsers.add_parser('plugin', help='Plugin management')
    plugin_subparsers = plugin_parser.add_subparsers(dest='plugin_command', help='plugin commands')

    # plugin list
    list_parser = plugin_subparsers.add_parser('list', help='List all plugins')
    list_parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed information')

    # plugin info
    info_parser = plugin_subparsers.add_parser('info', help='Show plugin information')
    info_parser.add_argument('plugin_name', help='Name of the plugin')

    # plugin create
    create_parser = plugin_subparsers.add_parser('create', help='Create a new plugin')
    create_parser.add_argument('plugin_name', help='Name for the new plugin')
    create_parser.add_argument('--template', choices=['basic', 'logger', 'auth'],
                               default='basic', help='Template to use')

    # plugin enable
    enable_parser = plugin_subparsers.add_parser('enable', help='Enable a plugin')
    enable_parser.add_argument('plugin_name', help='Name of the plugin to enable')

    # plugin disable
    disable_parser = plugin_subparsers.add_parser('disable', help='Disable a plugin')
    disable_parser.add_argument('plugin_name', help='Name of the plugin to disable')

    # plugin install
    install_parser = plugin_subparsers.add_parser('install', help='Install plugin dependencies')
    install_parser.add_argument('plugin_name', help='Name of the plugin')

    general_group = parser.add_argument_group("general")
    general_group.add_argument(
        "--curl", help="generates curl script", action="store_const", const=True
    )
    property_group = parser.add_argument_group("property")
    property_group.add_argument("--property-file", "-p", help="property file")
    general_group.add_argument(
        "--no-cookie",
        "-nc",
        help="cookie storage is disabled",
        action="store_const",
        const=True,
    )
    property_group.add_argument(
        "--env",
        "-e",
        help="environment to select in property file. properties will be enabled on FIFO",
        nargs="+",
        default=["*"],
    )
    general_group.add_argument(
        "--debug",
        "-d",
        help="debug will enable logs and exceptions",
        action="store_const",
        const=True,
    )
    general_group.add_argument(
        "--info", "-i", help="more information", action="store_const", const=True
    )
    fmt_group = parser.add_argument_group("format")
    fmt_group.add_argument(
        "--format", "-fmt", help="format http file", action="store_const", const=True
    )
    property_group.add_argument(
        "--experimental",
        "--b",
        help="enable experimental",
        action="store_const",
        const=True,
    )
    fmt_group.add_argument(
        "--stdout", help="print to commandline", action="store_const", const=True
    )
    property_group.add_argument(
        "--property", help="list of property's", nargs="+", default=[]
    )
    general_group.add_argument("file", nargs='?', help="http file")
    general_group.add_argument(
        "--target", "-t", help="targets a particular http definition", type=str
    )
    args = parser.parse_args()

    # Handle plugin commands
    if args.command == 'plugin':
        if not args.plugin_command:
            plugin_parser.print_help()
            sys.exit(1)
        from .plugin_system.cli import run_cli
        run_cli(args)
        return

    # Require file for normal execution
    if not args.file:
        parser.print_help()
        sys.exit(1)

    if args.debug and args.info:
        eprint("info and debug are conflicting options, use debug for more information")
        sys.exit(1)
    for one_prop in args.property:
        if "=" not in one_prop:
            # FUTURE,
            # this can be done better by adding validation in add_argument.
            eprint(f"command line property: `{one_prop}` is invalid, expected prop=val")
            sys.exit(1)
    config = Config(
        curl=args.curl,
        property_file=args.property_file,
        env=args.env,
        debug=args.debug,
        file=args.file,
        info=args.info,
        properties=args.property,
        no_cookie=args.no_cookie,
        target=args.target,
        format=args.format,
        stdout=args.stdout,
        experimental=args.experimental,
    )
    apply(config)


if __name__ == "__main__":
    main()
