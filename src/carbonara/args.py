"""The command line's vocabulary: the parser, the exit codes, and the types."""

import argparse
from importlib import metadata

from . import registry

# 0 and 1 return through main(). 2 never does: argparse hardcodes it in
# ArgumentParser.error(), which calls sys.exit(2) itself, and the --version
# action exits 0 the same way. Both unwind past main() as SystemExit, so 2
# exists to be asserted against rather than returned.
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ARGPARSE = 2

PROG = "carbonara"


def installed_version():
    """Return the version of the installed carbonara distribution."""
    try:
        return metadata.version("carbonara")
    except metadata.PackageNotFoundError:
        return "unknown (not installed)"


def version_line():
    """Return the program name and the installed version on one line."""
    return f"{PROG} {installed_version()}"


def temperature(value):
    """Parse a sampling temperature, rejecting anything outside 0.0 to 2.0."""
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from None
    if not 0.0 <= number <= 2.0:
        raise argparse.ArgumentTypeError(f"{number} is outside 0.0 to 2.0")
    return number


def delay(value):
    """Parse a per-token stream delay in seconds, which cannot be negative."""
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from None
    if number < 0:
        raise argparse.ArgumentTypeError(f"{number} is negative")
    return number


def build_parser():
    """Build the parser for every command.

    `--version` stays on the top-level parser alone, so asking a command for
    the version is an unknown flag and exits 2.
    """
    parser = argparse.ArgumentParser(prog=PROG, allow_abbrev=False)
    parser.add_argument(
        "--version",
        action="version",
        version=version_line(),
        help="print the installed version and exit",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser(
        "list", allow_abbrev=False, help="show the stacks and their state"
    )

    prep = commands.add_parser(
        "prep", allow_abbrev=False, help="prep a stack's station"
    )
    prep.add_argument("stack", nargs="?", choices=registry.NAMES)
    prep.add_argument(
        "--latest",
        action="store_true",
        help="install from requirements.txt instead of the pinned set",
    )
    prep.add_argument(
        "--docker",
        action="store_true",
        help="build a Docker image instead of a virtual environment",
    )

    cook = commands.add_parser(
        "cook-with", allow_abbrev=False, help="cook the demo with one stack"
    )
    cook.add_argument("stack", nargs="?", choices=registry.NAMES)
    cook.add_argument("--order", metavar="TEXT", help="the order to give the kitchen")
    cook.add_argument(
        "--model",
        metavar="NAME",
        help=f"Ollama model (default {registry.DEFAULT_MODEL})",
    )
    cook.add_argument("--temperature", metavar="N", type=temperature, help="0.0 to 2.0")
    cook.add_argument(
        "--stream-delay", metavar="N", type=delay, help="seconds per token"
    )
    cook.add_argument(
        "--telemetry",
        action="store_true",
        help="leave the frameworks' own telemetry defaults alone",
    )
    cook.add_argument(
        "--docker",
        action="store_true",
        help="cook in a Docker container instead of a virtual environment",
    )

    commands.add_parser(
        "version", allow_abbrev=False, help="print the installed version and exit"
    )

    return parser
