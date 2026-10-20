"""
# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# contact: east-van-ai@proton.me
# ==============================================
#
# ~~~ ~~~ ~~~ ~~~ ~~~ carbonara ~~~ ~~~ ~~~ ~~~ ~~~
#
# One agentic AI demo, four agent stacks, one command. A dispatcher takes
# a plain English order, an expeditor reasons out which workers to call
# and in what sequence, and the workers each do one job. Nobody hardcodes
# the sequence. The model works it out, and watching it reason is the
# demo.
#
# The same scenario is built four times over, once per agent stack.
# carbonara imports none of them. Each stack gets its own interpreter and
# its own virtual environment, because crewai refuses Python 3.14 and the
# other three want it.
#
# Usage:
#
#    carbonara list
#    carbonara prep STACK [--latest] [--docker]
#    carbonara cook-with STACK [--order TEXT] [--model NAME] [--temperature N]
#    carbonara cook-with STACK [--telemetry] [--docker]
#    carbonara clean STACK [--docker]
#
# Commands:
#
#    list                show every stack, the interpreter it wants,
#                        whether its environment and its Docker image
#                        are built, and which of them calls home.
#                        Read-only.
#    prep STACK          build that stack's environment, or its Docker
#                        image with --docker. Pinned unless --latest
#                        says otherwise.
#    cook-with STACK     cook the demo with that stack, in a container
#                        with --docker. Preps its station first if this
#                        is its first cook.
#    clean STACK         remove that stack's environment, or its Docker
#                        image and the locked network with --docker, so
#                        the next prep starts from scratch.
#
# STACK is one of: no-framework, crewai, langgraph, smolagents.
#
# Calling home:
#
#    Two of the four stacks reach the network on their own account, and
#    neither asks first. crewai sends its own telemetry. smolagents
#    fetches a price list through LiteLLM, a library underneath it.
#    langgraph stays home until someone turns on LangSmith tracing,
#    and no-framework has nothing that could call at all. It is the most
#    interesting thing the four have to say about each other.
#
#    carbonara silences both before it runs anything. Every switch they
#    honour goes off, and crewai's tracing prompt is answered with a no
#    in its own consent file. `carbonara list` shows which stack is
#    which. --telemetry hands them back their own defaults.
#
# Run prep, cook-with, or clean with nothing after it for its own documentation,
# including the options it takes:
#
#    carbonara prep
#    carbonara cook-with
#    carbonara clean
#
# list takes no STACK, so bare `carbonara list` runs rather than
# documenting itself.
#
# STACK comes first, then flags, whose order among themselves is free.
# Spell flags in full: an abbreviation like `--temp` is rejected, so it
# can never stand in for `--temperature`. Bare `carbonara` prints this
# text and exits 0. Asking is not a usage error.
#
# carbonara reads no piped input.
#
# Exit codes:
#
#    0:     success, and documentation
#    1:     carbonara's own error, a STACK missing or stray, or a
#           readiness failure: no interpreter, no Ollama, no model,
#           no Docker
#    2:     an unknown command, an unknown flag, or a bad value
#
# License: MIT
# ==============================================
"""

import sys

from . import cli_clean, cli_cook_with, cli_list, cli_prep, registry
from .args import EXIT_ARGPARSE, EXIT_ERROR, EXIT_OK, build_parser, version_line

__all__ = ["EXIT_ARGPARSE", "EXIT_ERROR", "EXIT_OK", "main"]

# Each command's surface module carries its own documentation, usage line,
# and run(). Every command but list reads the same single STACK slot.
COMMANDS = {
    "list": cli_list,
    "prep": cli_prep,
    "cook-with": cli_cook_with,
    "clean": cli_clean,
}

# list acts on the whole registry, so there is no argument for it to be
# missing. Its bare form is a complete command line, not a question.
STACKLESS = {"list"}

# version is missing from both on purpose. It has no command module, so main()
# answers it directly, and its stray-word error reaches for this usage line.
VERSION_USAGE = "carbonara version"


def leading_paths(tokens):
    """Return the tokens ahead of the first flag.

    The documented grammar puts STACK before every flag, so the slot is read
    off the front of the command line. What argparse resolved from anywhere
    else is discarded, since how much it tolerates depends on the interpreter.
    """
    paths = []
    for token in tokens:
        if token.startswith("-"):
            break
        paths.append(token)
    return paths


def usage_error(usage, message):
    """Report a command line carbonara could not read, with the matching usage."""
    print(f"carbonara: {message}", file=sys.stderr)
    print(f"Usage: {usage}", file=sys.stderr)
    return EXIT_ERROR


def main():
    """Parse arguments, enforce the CLI grammar, and dispatch to a command.

    A bare word is a question and gets documentation, exit 0, except where the
    command takes no argument. Any other shortfall in the STACK slot is a slip
    and gets an error, exit 1. Argparse keeps the vocabulary it owns: an
    unknown command, an unknown flag, or a bad value, exiting 2.
    """
    tokens = sys.argv[1:]

    if not tokens:
        print(__doc__.strip())
        return EXIT_OK

    if len(tokens) == 1 and tokens[0] in COMMANDS and tokens[0] not in STACKLESS:
        print(COMMANDS[tokens[0]].__doc__.strip())
        return EXIT_OK

    parser = build_parser()
    args, extras = parser.parse_known_args(tokens)

    if any(extra.startswith("-") for extra in extras):
        parser.parse_args(tokens)  # argparse names the flag better, exit 2

    if args.command == "version":
        strays = leading_paths(tokens[1:])
        if strays:
            return usage_error(
                VERSION_USAGE, f"version takes no arguments: {strays[0]!r}"
            )
        print(version_line())
        return EXIT_OK

    module = COMMANDS[args.command]

    if args.command in STACKLESS:
        strays = leading_paths(tokens[1:])
        if strays:
            return usage_error(
                module.USAGE, f"{args.command} takes no arguments: {strays[0]!r}"
            )
        return module.run(args)

    # Not args.stack: what argparse resolves from a token after a flag varies
    # by interpreter, and the grammar should not.
    names = leading_paths(tokens[1:])
    if not names:
        return usage_error(module.USAGE, f"{args.command} needs STACK")
    if len(names) > 1:
        return usage_error(
            module.USAGE, f"{args.command} takes nothing after STACK: {names[1]!r}"
        )

    stack = registry.find(names[0])
    if stack is None:
        return usage_error(module.USAGE, f"unknown stack {names[0]!r}")

    return module.run(stack, args)


if __name__ == "__main__":
    sys.exit(main())
