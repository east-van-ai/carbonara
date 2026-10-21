"""The command line's vocabulary: the parser, the subparsers, and the types."""

import argparse
import sys
from importlib import metadata

from . import cli_clean, cli_cook_with, cli_list, cli_prep, registry

PROG = "carbonara"

# On 3.14 argparse colours help on a terminal. carbonara's help stays plain.
MONOCHROME = {"color": False} if sys.version_info >= (3, 14) else {}

STACK_ARG = f"""\
stack:
  STACK     the agent stack to act on, one of: {", ".join(registry.NAMES)}.
  STACK comes right after COMMAND, then options in any order."""

# The ways a stack can run. A STACK command takes exactly one, and has no default.
MODES = ("--venv", "--docker")

# The stacks' own defaults, which the help names. A test pins them against
# each stack script.
DEFAULT_ORDER = "make me a carbonara"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_STREAM_DELAY = 0.0


def leading_paths(tokens):
    """Return the tokens ahead of the first flag."""
    paths = []
    for token in tokens:
        if token.startswith("-"):
            break
        paths.append(token)
    return paths


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


def add_stack(parser):
    """Add the STACK positional, in a group of its own so every page ends on it."""
    parser.add_argument_group("stack").add_argument(
        "stack",
        nargs="?",
        metavar="STACK",
        choices=registry.NAMES,
        help=f"one of: {', '.join(registry.NAMES)}",
    )


def add_mode(parser, venv_help, docker_help):
    """Add --venv and --docker under a `mode` heading, so at most one is given."""
    either = parser.add_argument_group("mode").add_mutually_exclusive_group()
    either.add_argument("--venv", action="store_true", help=venv_help)
    either.add_argument("--docker", action="store_true", help=docker_help)


def add_list(subparsers):
    """Add the `list` subparser and return it."""
    return subparsers.add_parser(
        "list", help=cli_list.HELP, usage=cli_list.USAGE, allow_abbrev=False
    )


def add_prep(subparsers):
    """Add the `prep` subparser and return it."""
    prep = subparsers.add_parser(
        "prep", help=cli_prep.HELP, usage=cli_prep.USAGE, allow_abbrev=False
    )
    prep.add_argument(
        "--latest",
        action="store_true",
        help="install from requirements.txt (default: requirements-pinned.txt)",
    )
    add_mode(
        prep,
        "build the stack's virtual environment",
        "build the stack's Docker image",
    )
    add_stack(prep)
    return prep


def add_cook_with(subparsers):
    """Add the `cook-with` subparser and return it."""
    cook = subparsers.add_parser(
        "cook-with",
        help=cli_cook_with.HELP,
        usage=cli_cook_with.USAGE,
        allow_abbrev=False,
    )
    cook.add_argument(
        "--order",
        metavar="TEXT",
        help=f"the order to give the kitchen (default: {DEFAULT_ORDER})",
    )
    cook.add_argument(
        "--model",
        metavar="NAME",
        help=f"the Ollama model (default: {registry.DEFAULT_MODEL})",
    )
    cook.add_argument(
        "--temperature",
        metavar="N",
        type=temperature,
        help=f"sampling temperature, 0.0 to 2.0 (default: {DEFAULT_TEMPERATURE})",
    )
    cook.add_argument(
        "--stream-delay",
        metavar="N",
        type=delay,
        help=f"seconds per token, no-framework only (default: {DEFAULT_STREAM_DELAY})",
    )
    cook.add_argument(
        "--telemetry",
        action="store_true",
        help="leave the frameworks' own telemetry defaults alone, "
        "and the Docker network open",
    )
    add_mode(
        cook,
        "cook in the stack's virtual environment",
        "cook in a Docker container, behind a locked network",
    )
    add_stack(cook)
    return cook


def add_clean(subparsers):
    """Add the `clean` subparser and return it."""
    clean = subparsers.add_parser(
        "clean", help=cli_clean.HELP, usage=cli_clean.USAGE, allow_abbrev=False
    )
    add_mode(
        clean,
        "remove the stack's virtual environment",
        "remove the stack's Docker image and the locked network",
    )
    add_stack(clean)
    return clean


def build_parser():
    """Build the parser for every command.

    `--version` stays on the top-level parser alone, so asking a command for
    the version is an unknown flag and exits 2.
    """
    parser = argparse.ArgumentParser(
        prog=PROG,
        usage="\n       ".join(
            [
                cli_list.USAGE,
                cli_prep.USAGE,
                cli_cook_with.USAGE,
                cli_clean.USAGE,
                f"{PROG} version",
            ]
        ),
        epilog=STACK_ARG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        **MONOCHROME,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=version_line(),
        help="print the installed version and exit",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)
    add_list(subparsers)
    add_prep(subparsers)
    add_cook_with(subparsers)
    add_clean(subparsers)
    subparsers.add_parser(
        "version", help="print the installed version and exit", allow_abbrev=False
    )
    return parser


def command_help(add_command):
    """Return one command's own `--help` text, as argparse prints it."""
    subparsers = argparse.ArgumentParser(prog=PROG, **MONOCHROME).add_subparsers()
    return add_command(subparsers).format_help()
