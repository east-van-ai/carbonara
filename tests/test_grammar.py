"""The accepted command line, pinned.

A command line that drifts from the documented grammar still parses. It just
means something else, so nothing fails on its own when the shape moves. That is
what this file is for.
"""

import re

import pytest

from carbonara import (
    args,
    cli,
    cli_clean,
    cli_cook_with,
    cli_prep,
    containers,
    environ,
    registry,
    shared,
)
from carbonara.args import build_parser
from carbonara.cli import EXIT_ARGPARSE, EXIT_ERROR, EXIT_OK

#: Each STACK command, its module, and the function that adds its subparser.
PAGES = {
    "prep": (cli_prep, args.add_prep),
    "cook-with": (cli_cook_with, args.add_cook_with),
    "clean": (cli_clean, args.add_clean),
}

#: Every flag on every command, with a value where it takes one.
FLAGS = [
    ("prep", "--latest"),
    ("prep", "--venv"),
    ("prep", "--docker"),
    ("cook-with", "--order", "x"),
    ("cook-with", "--model", "x"),
    ("cook-with", "--temperature", "0.5"),
    ("cook-with", "--stream-delay", "0.1"),
    ("cook-with", "--telemetry"),
    ("cook-with", "--venv"),
    ("cook-with", "--docker"),
    ("clean", "--venv"),
    ("clean", "--docker"),
]


@pytest.fixture
def unreached(monkeypatch):
    """Make every command's action fail the test if it is ever reached."""

    def reached(*arguments):
        raise AssertionError("the action ran")

    for module in (cli_prep, cli_cook_with, cli_clean):
        monkeypatch.setattr(module, "run", reached)


def test_bare_tool_prints_the_banner_then_help(invoke):
    """Bare carbonara is a question: the banner, then --help, exit 0."""
    code, out, _ = invoke()
    assert code == EXIT_OK
    assert out.startswith("# ===")
    assert "\n        carbonara\n" in out
    assert "exit codes:" in out
    assert out.rstrip().endswith(build_parser().format_help().rstrip())
    below_signature = out.split("# ===", 3)[-1].split("\n", 1)[1]
    assert not any(line.startswith("#") for line in below_signature.splitlines())


@pytest.mark.parametrize("command", PAGES)
def test_bare_command_word_prints_its_own_page(invoke, command):
    """A command word alone prints its docstring, then its own --help, exit 0."""
    _, add_command = PAGES[command]
    code, out, _ = invoke(command)
    assert code == EXIT_OK
    assert out.startswith(f"        carbonara -- {command}\n")
    assert out.rstrip().endswith(args.command_help(add_command).rstrip())


@pytest.mark.parametrize("command", PAGES)
def test_bare_page_carries_the_stack_table(invoke, command):
    """The table sits between the docstring and --help, one row per stack."""
    module, add_command = PAGES[command]
    _, out, _ = invoke(command)
    doc = module.__doc__.strip("\n")
    help_text = args.command_help(add_command).rstrip()
    assert out.rstrip() == f"{doc}\n\n{shared.stack_table()}\n\n{help_text}"
    assert "CALLS HOME" in out
    for name in registry.NAMES:
        assert f"  {name}  " in out


@pytest.mark.parametrize("command", PAGES)
def test_help_flag_carries_no_table(invoke, command):
    """Only the bare word looks at the world; --help stays argparse's alone."""
    _, out, _ = invoke(command, "--help")
    assert "CALLS HOME" not in out


@pytest.mark.parametrize("command", PAGES)
def test_bare_page_without_docker_still_documents(invoke, monkeypatch, command):
    """With no Docker, the IMAGE column says so and the page still exits 0."""
    monkeypatch.setattr(
        containers, "check_docker", lambda: environ.Check(False, "no docker", "x")
    )
    code, out, _ = invoke(command)
    assert code == EXIT_OK
    assert "no docker" in out


@pytest.mark.parametrize("command", PAGES)
def test_bare_page_never_asks_ollama(invoke, monkeypatch, command):
    """Ollama belongs to list's footer, not to a page about picking a stack."""

    def asked(*arguments, **keywords):
        raise AssertionError("the page asked Ollama")

    monkeypatch.setattr(environ, "check_ollama", asked)
    code, _, _ = invoke(command)
    assert code == EXIT_OK


def test_list_probes_docker_once(invoke, monkeypatch):
    """list hands its own Docker check to the table rather than probing twice."""
    calls = []

    def counted():
        calls.append(1)
        return environ.Check(True)

    monkeypatch.setattr(containers, "check_docker", counted)
    invoke("list")
    assert len(calls) == 1


@pytest.mark.parametrize("command", PAGES)
def test_command_help_opens_on_its_usage(invoke, command):
    """--help on a command reads STACK first, as its USAGE does."""
    module, _ = PAGES[command]
    code, out, _ = invoke(command, "--help")
    assert code == EXIT_OK
    assert out.startswith(f"usage: {module.USAGE}\n")


@pytest.mark.parametrize("arguments", [(), ("--help",), *((c,) for c in PAGES)])
def test_help_prints_no_colour(invoke, monkeypatch, arguments):
    """Under FORCE_COLOR, the banner and every page stay plain."""
    monkeypatch.setenv("FORCE_COLOR", "1")
    _, out, _ = invoke(*arguments)
    assert "\x1b" not in out


def test_bare_list_runs_rather_than_documenting(invoke):
    """list takes no argument, so its bare form is complete and runs."""
    code, out, _ = invoke("list")
    assert code == EXIT_OK
    assert "CALLS HOME" in out
    assert "no-framework" in out


@pytest.mark.parametrize("command", ["list", "version"])
def test_a_slotless_command_rejects_a_stray_word(invoke, command):
    """A word after list or version is a usage error, with that row's usage."""
    code, out, err = invoke(command, "extra")
    assert code == EXIT_ERROR
    assert out == ""
    assert f"carbonara: {command} takes nothing after it: 'extra'" in err
    assert f"Usage: {cli.COMMANDS[command].usage}" in err


@pytest.mark.parametrize("command", PAGES)
def test_missing_stack_is_an_error_not_help(invoke, unreached, command):
    """Once any other token is present, a missing STACK is a slip, exit 1."""
    flag = {"prep": "--latest", "cook-with": "--order=x", "clean": "--docker"}[command]
    code, _, err = invoke(command, flag)
    assert code == EXIT_ERROR
    assert f"carbonara: {command} needs STACK" in err
    assert f"Usage: {PAGES[command][0].USAGE}" in err


def test_stack_after_a_flag_is_not_accepted(invoke, unreached):
    """The documented grammar puts STACK before the flags, and only there.

    Since 3.12 argparse back-fills a trailing optional positional from a token
    after any number of flags, so this parses happily unless the slot is read
    off the front of the line instead.
    """
    code, _, err = invoke("cook-with", "--order", "hi", "crewai")
    assert code == EXIT_ERROR
    assert "needs STACK" in err


def test_a_second_bare_word_is_named(invoke, unreached):
    """A stray word after STACK is named by carbonara, not left to argparse."""
    code, _, err = invoke("cook-with", "crewai", "extra")
    assert code == EXIT_ERROR
    assert "carbonara: cook-with takes nothing after STACK: 'extra'" in err
    assert f"Usage: {cli_cook_with.USAGE}" in err


@pytest.mark.parametrize("flag", FLAGS, ids=lambda flag: " ".join(flag))
@pytest.mark.parametrize("stray", ["extra", "langgraph"])
def test_a_stray_word_after_every_flag_is_refused(invoke, unreached, flag, stray):
    """A bare word behind a flag is a stray, and the command never runs.

    The slot checks cannot see that position. Before this test, `clean crewai
    --docker extra` removed the image and the network.
    """
    command, *option = flag
    code, out, err = invoke(command, "crewai", *option, stray)
    assert code == EXIT_ERROR
    assert out == ""
    assert f"carbonara: {command} takes nothing after STACK: {stray!r}" in err
    assert f"Usage: {PAGES[command][0].USAGE}" in err


@pytest.mark.parametrize("command", PAGES)
def test_a_missing_mode_is_a_slip(invoke, unreached, command):
    """No mode is a default, so STACK alone is refused, exit 1, and nothing runs."""
    code, out, err = invoke(command, "crewai")
    assert code == EXIT_ERROR
    assert out == ""
    assert f"carbonara: {command} needs --venv or --docker" in err
    assert f"Usage: {PAGES[command][0].USAGE}" in err


@pytest.mark.parametrize(
    "arguments", [("prep", "--latest"), ("cook-with", "--telemetry")]
)
def test_a_missing_stack_is_named_before_a_missing_mode(invoke, unreached, arguments):
    """The slot is checked first, so the first thing wrong is the first named."""
    code, _, err = invoke(*arguments)
    assert code == EXIT_ERROR
    assert f"carbonara: {arguments[0]} needs STACK" in err
    assert "--venv or --docker" not in err


def test_a_stray_word_is_named_before_a_missing_mode(invoke, unreached):
    """A stray word is a slot error, so it wins over the missing mode."""
    code, _, err = invoke("clean", "crewai", "extra")
    assert code == EXIT_ERROR
    assert "carbonara: clean takes nothing after STACK: 'extra'" in err


@pytest.mark.parametrize("command", PAGES)
@pytest.mark.parametrize("mode", ["--venv", "--docker"])
def test_each_mode_reaches_the_command(invoke, monkeypatch, command, mode):
    """Either flag alone runs the command, and docker says which one was named."""
    seen = []
    module, _ = PAGES[command]
    monkeypatch.setattr(module, "run", lambda stack, parsed: seen.append(parsed))
    code, _, _ = invoke(command, "crewai", mode)
    assert code == EXIT_OK
    assert [parsed.docker for parsed in seen] == [mode == "--docker"]


def test_version_is_documentation(invoke):
    """--version prints the program name and a number, exit 0."""
    code, out, _ = invoke("--version")
    assert code == EXIT_OK
    assert out.startswith("carbonara ")


def test_version_command_word_is_documentation(invoke):
    """version prints the program name and a number, exit 0."""
    code, out, _ = invoke("version")
    assert code == EXIT_OK
    assert out.startswith("carbonara ")


def test_both_version_spellings_print_the_same_line(invoke):
    """version and --version share one helper, so their lines cannot drift."""
    _, word, _ = invoke("version")
    _, flag, _ = invoke("--version")
    assert word == flag


@pytest.mark.parametrize(
    "arguments",
    [
        ("frobnicate",),
        ("cook-with", "nosuch"),
        ("cook-with", "crewai", "--nope"),
        ("cook-with", "crewai", "--temp", "0.8"),
        ("cook-with", "crewai", "--temperature", "9"),
        ("cook-with", "crewai", "--temperature", "hot"),
        ("list", "--version"),
        ("version", "--version"),
        ("version", "--latest"),
        ("list", "--docker"),
        ("clean", "nosuch"),
        ("clean", "crewai", "--latest"),
        ("prep", "crewai", "--venv", "--docker"),
        ("cook-with", "crewai", "--docker", "--venv"),
        ("clean", "crewai", "--venv", "--docker"),
        ("list", "--venv"),
        ("version", "--venv"),
    ],
    ids=[
        "unknown command",
        "unknown stack",
        "unknown flag",
        "abbreviated flag",
        "temperature out of range",
        "temperature not a number",
        "version on a command",
        "version on the version command",
        "unknown flag on version",
        "docker on list",
        "unknown stack on clean",
        "latest on clean",
        "both modes on prep",
        "both modes on cook-with",
        "both modes on clean",
        "venv on list",
        "venv on version",
    ],
)
def test_argparse_keeps_the_vocabulary_it_owns(invoke, arguments):
    """Unknown words, unknown flags, and bad values are argparse's, exit 2."""
    code, _, _ = invoke(*arguments)
    assert code == EXIT_ARGPARSE


@pytest.mark.parametrize("command", PAGES)
def test_docker_is_a_flag_on_the_stack_commands(command):
    """--docker sits after STACK on every stack command, and is off by default."""
    parser = build_parser()
    assert parser.parse_args([command, "crewai", "--docker"]).docker is True
    assert parser.parse_args([command, "crewai"]).docker is False


def stack_default(stack, variable):
    """Read the default a stack script gives one CARBONARA_* variable, if any."""
    source = stack.script.read_text()
    found = re.search(rf'os\.environ\.get\("{variable}", "([^"]*)"\)', source)
    return found.group(1) if found else None


@pytest.mark.parametrize("stack", registry.stacks(), ids=lambda stack: stack.name)
def test_the_help_names_the_stacks_own_defaults(stack):
    """The help states each default, so it must match what the scripts read."""
    assert stack_default(stack, "CARBONARA_ORDER") == args.DEFAULT_ORDER
    assert stack_default(stack, "CARBONARA_MODEL") == registry.DEFAULT_MODEL
    assert float(stack_default(stack, "CARBONARA_TEMPERATURE")) == (
        args.DEFAULT_TEMPERATURE
    )
    delay = stack_default(stack, "CARBONARA_STREAM_DELAY")
    if stack.name == "no-framework":
        assert float(delay) == args.DEFAULT_STREAM_DELAY
    else:
        assert delay is None, "--stream-delay's help says no-framework only"
