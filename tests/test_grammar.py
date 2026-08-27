"""The accepted command line, pinned.

A command line that drifts from the documented grammar still parses. It just
means something else, so nothing fails on its own when the shape moves. That is
what this file is for.
"""

import pytest

from carbonara.args import EXIT_ARGPARSE, EXIT_ERROR, EXIT_OK


def test_bare_tool_prints_the_banner(invoke):
    """Bare carbonara is a question and gets the banner, exit 0."""
    code, out, _ = invoke()
    assert code == EXIT_OK
    assert "~~~ carbonara ~~~" in out
    assert "Exit codes:" in out


@pytest.mark.parametrize("command", ["prep", "cook-with"])
def test_bare_command_word_prints_its_own_doc(invoke, command):
    """A command word alone prints that command's documentation, exit 0."""
    code, out, _ = invoke(command)
    assert code == EXIT_OK
    assert f"~~~ carbonara {command} ~~~" in out
    assert all(line.startswith("#") for line in out.splitlines() if line)


def test_bare_list_runs_rather_than_documenting(invoke):
    """list takes no argument, so its bare form is complete and runs."""
    code, out, _ = invoke("list")
    assert code == EXIT_OK
    assert "CARBONARA LIST" not in out
    assert "no-framework" in out


def test_list_rejects_a_stray_word(invoke):
    """A word after list is a usage error, not a silently ignored token."""
    code, _, err = invoke("list", "extra")
    assert code == EXIT_ERROR
    assert "takes no arguments" in err
    assert "Usage: carbonara list" in err


@pytest.mark.parametrize("command", ["prep", "cook-with"])
def test_missing_stack_is_an_error_not_help(invoke, command):
    """Once any other token is present, a missing STACK is a slip, exit 1."""
    code, _, err = invoke(command, "--latest" if command == "prep" else "--order=x")
    assert code == EXIT_ERROR
    assert "needs STACK" in err
    assert "Usage:" in err


def test_stack_after_a_flag_is_not_accepted(invoke):
    """The documented grammar puts STACK before the flags, and only there.

    Since 3.12 argparse back-fills a trailing optional positional from a token
    after any number of flags, so this parses happily unless the slot is read
    off the front of the line instead.
    """
    code, _, err = invoke("cook-with", "--order", "hi", "crewai")
    assert code == EXIT_ERROR
    assert "needs STACK" in err


def test_a_second_bare_word_is_named(invoke):
    """A stray word after STACK is named by carbonara, not left to argparse."""
    code, _, err = invoke("cook-with", "crewai", "extra")
    assert code == EXIT_ERROR
    assert "'extra'" in err


def test_version_is_documentation(invoke):
    """--version prints the program name and a number, exit 0."""
    code, out, _ = invoke("--version")
    assert code == EXIT_OK
    assert out.startswith("carbonara ")


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
    ],
    ids=[
        "unknown command",
        "unknown stack",
        "unknown flag",
        "abbreviated flag",
        "temperature out of range",
        "temperature not a number",
        "version on a command",
    ],
)
def test_argparse_keeps_the_vocabulary_it_owns(invoke, arguments):
    """Unknown words, unknown flags, and bad values are argparse's, exit 2."""
    code, _, _ = invoke(*arguments)
    assert code == EXIT_ARGPARSE
