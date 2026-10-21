"""
# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai/carbonara
# contact: east-van-ai@proton.me
# license: MIT
# ==============================================

        carbonara

One agentic AI demo, four agent stacks, one command. A dispatcher takes a
plain English order, an expeditor reasons out which workers to call and in
what order, and each worker does one job. Nobody hardcodes the sequence: the
model works it out, and watching it reason is the demo. The same scenario is
built once per stack, crewai, langgraph, smolagents, and plain Python, each
in an interpreter and a virtual environment of its own, or a container. See
where things stand with `carbonara list`, and cook with `carbonara cook-with
STACK --venv`, or `--docker`.

Run a command with nothing after it for its own page. list takes no STACK,
so bare `carbonara list` runs instead.

calling home:
    crewai sends its own telemetry, and smolagents fetches a price list
    through LiteLLM. Neither asks first. carbonara turns every switch they
    honour off before it runs anything, and --telemetry on a cook hands them
    back their own defaults. `carbonara list` shows which stack is which.

piped input:
    carbonara reads none.

exit codes:
    0:     success, and documentation
    1:     carbonara's own error: a STACK missing or stray, no --venv or
           --docker, a readiness failure (no interpreter, no Ollama, no
           model, no Docker), or a build or removal that failed partway
    2:     an unknown command, an unknown option, a bad value, an unknown
           STACK, or --venv and --docker together
    130:   stopped by Ctrl-C, with the stack and any relay stopped first
    143:   stopped by SIGTERM, the same way
    other: a cook exits with the stack's own exit code
"""

import signal
import sys
from collections import namedtuple

from . import (
    args,
    cli_clean,
    cli_cook_with,
    cli_list,
    cli_prep,
    errors,
    registry,
    shared,
)

# 2 never returns through main(): argparse's error() and the --version action
# call sys.exit() themselves. It exists to be asserted against.
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ARGPARSE = 2

Command = namedtuple("Command", "bare usage slots modes action")
"""A command word's answer to being typed alone, its usage line, the slots it
reads, the mode flags it needs one of, and the action a full invocation runs.

`bare` returns the text for the bare word; `action` runs the command and
returns None, or an exit code of its own. For `list` and `version`, both read
from the same function, since running the command answers the bare word.
"""


def command_page(module, add_command):
    """Return a command's bare page: its docstring, the stack table, then its --help."""
    doc = module.__doc__.strip("\n")  # not strip(): the title's indent is layout
    help_text = args.command_help(add_command).rstrip()
    return f"{doc}\n\n{shared.stack_table()}\n\n{help_text}"


def on_stack(module):
    """Return an action that runs a STACK command on the stack it names."""
    return lambda paths, parsed: module.run(registry.find(paths[0]), parsed)


COMMANDS = {
    "list": Command(
        cli_list.table,
        cli_list.USAGE,
        cli_list.SLOTS,
        (),
        lambda paths, parsed: print(cli_list.table()),
    ),
    "prep": Command(
        lambda: command_page(cli_prep, args.add_prep),
        cli_prep.USAGE,
        cli_prep.SLOTS,
        args.MODES,
        on_stack(cli_prep),
    ),
    "cook-with": Command(
        lambda: command_page(cli_cook_with, args.add_cook_with),
        cli_cook_with.USAGE,
        cli_cook_with.SLOTS,
        args.MODES,
        on_stack(cli_cook_with),
    ),
    "clean": Command(
        lambda: command_page(cli_clean, args.add_clean),
        cli_clean.USAGE,
        cli_clean.SLOTS,
        args.MODES,
        on_stack(cli_clean),
    ),
    "version": Command(
        args.version_line,
        "carbonara version",
        (),
        (),
        lambda paths, parsed: print(args.version_line()),
    ),
}


def usage_error(usage, message):
    """Report a command line carbonara could not read, with the matching usage."""
    sys.stdout.flush()
    print(f"carbonara: {message}", file=sys.stderr)
    print(f"Usage: {usage}", file=sys.stderr)
    return EXIT_ERROR


def readiness_error(message):
    """Report what the run needed and did not find, with no usage line."""
    sys.stdout.flush()
    print(f"carbonara: {message}", file=sys.stderr)
    return EXIT_ERROR


def stopped(message, code):
    """Report a run a signal stopped, once its child and any relay are gone."""
    sys.stdout.flush()
    print(f"carbonara: {message}", file=sys.stderr)
    return code


def raise_stopped(signum, frame):
    """Turn SIGTERM into an exception, so every finally on the way out still runs."""
    raise errors.Stopped(signum)


def runtime_error(message):
    """Report a run that stopped partway, naming what was written."""
    sys.stdout.flush()
    print(f"carbonara: {message}", file=sys.stderr)
    return EXIT_ERROR


def main(argv=None):
    """Parse arguments, run the matching command, return an exit code."""
    tokens = list(sys.argv[1:] if argv is None else argv)

    if not tokens:
        print(f"{__doc__.strip()}\n\n{args.build_parser().format_help().rstrip()}")
        return EXIT_OK

    # A command word and nothing else is a question, and its own page answers.
    if len(tokens) == 1 and tokens[0] in COMMANDS:
        print(COMMANDS[tokens[0]].bare())
        return EXIT_OK

    parser = args.build_parser()
    parsed, extras = parser.parse_known_args(tokens)

    if any(extra.startswith("-") for extra in extras):
        parser.parse_args(tokens)  # argparse names the flag better, exit 2

    paths = args.leading_paths(tokens[1:])

    command = COMMANDS[parsed.command]

    if len(paths) < len(command.slots):
        needed = " and ".join(command.slots)
        if len(command.slots) > 1:
            needed = f"both {needed}"
        return usage_error(command.usage, f"{parsed.command} needs {needed}")

    # A word past the slots is a stray, and so is one argparse left over after a flag.
    strays = paths[len(command.slots) :] or extras
    if strays:
        last = command.slots[-1] if command.slots else "it"
        return usage_error(
            command.usage,
            f"{parsed.command} takes nothing after {last}: {strays[0]!r}",
        )

    # No mode is a default, so a STACK command that names none is a slip.
    if command.modes and not any(getattr(parsed, m[2:]) for m in command.modes):
        either = " or ".join(command.modes)
        return usage_error(command.usage, f"{parsed.command} needs {either}")

    # 128 plus the signal number is the shell's own code for a run a signal ended.
    previous = signal.signal(signal.SIGTERM, raise_stopped)
    try:
        code = command.action(paths, parsed)
    except errors.ReadinessError as failure:
        return readiness_error(str(failure))
    except errors.RuntimeFailure as failure:
        return runtime_error(str(failure))
    except KeyboardInterrupt:
        return stopped("stopped by Ctrl-C", 128 + signal.SIGINT)
    except errors.Stopped as stop:
        return stopped(
            f"stopped by {signal.Signals(stop.signum).name}", 128 + stop.signum
        )
    finally:
        signal.signal(signal.SIGTERM, previous)

    return EXIT_OK if code is None else code


if __name__ == "__main__":
    sys.exit(main())
