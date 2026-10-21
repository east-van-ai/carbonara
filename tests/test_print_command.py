"""A cook prints the command it runs, and the printed command is the real one.

Rule 4 in CLAUDE.md: what is printed and what is run come from the same argv,
so a pasted command does what carbonara did.
"""

import shlex
import subprocess

import pytest

from carbonara import containers, environ, registry


@pytest.fixture
def ran(monkeypatch):
    """Stub subprocess.run, and hand back every argv it was given."""
    seen = []

    class Completed:
        returncode = 0

    def fake_run(argv, **kwargs):
        seen.append(argv)
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    return seen


@pytest.fixture
def built(monkeypatch):
    """Make every stack look built, as a venv and as an image."""
    monkeypatch.setattr(environ, "is_built", lambda stack: True)
    monkeypatch.setattr(containers, "is_built", lambda stack: True)


def printed_argv(out):
    """Read the printed command back as a shell would, from carbonara's output."""
    block = out.split("carbonara: running\n", 1)[1]
    lines = []
    for line in block.splitlines():
        lines.append(line.removesuffix(" \\"))
        if not line.endswith(" \\"):
            break
    return shlex.split(" ".join(lines))


def test_a_flag_keeps_its_value_on_its_line():
    """`--flag value` is one line, and a flag before a flag stands alone."""
    lines = environ.command_lines(["docker", "run", "--rm", "--env", "A=1", "img"])
    assert lines == ["docker run", "--rm", "--env A=1", "img"]


def test_each_assignment_gets_a_line():
    """In venv mode the variables come first, one per line."""
    lines = environ.command_lines(["env", "A=1", "B=2", "python", "x.py"])
    assert lines == ["env", "A=1", "B=2", "python x.py"]


def test_a_long_tail_takes_a_line_per_word():
    """Two long paths would make one unreadable line, so they split."""
    long = "/a" * 30
    lines = environ.command_lines(["env", "A=1", long + "/python", long + "/x.py"])
    assert lines[-2:] == [long + "/python", long + "/x.py"]


def test_a_path_with_a_space_comes_back_quoted():
    """macOS keeps crewai's consent under Application Support."""
    lines = environ.command_lines(["docker", "--volume", "/A B:/c", "img"])
    assert lines[1] == "--volume '/A B:/c'"


@pytest.mark.parametrize(
    "argv",
    [
        ["env", "A=1", "B=two words", "/p/python", "/p/x.py"],
        ["docker", "run", "--rm", "--volume", "/A B:/c:ro", "img", "python", "/x"],
    ],
)
def test_the_printed_command_reads_back_as_the_argv(capsys, argv):
    """Joined and split as a shell would, the print is the argv exactly."""
    environ.print_command(argv)
    assert printed_argv(capsys.readouterr().out) == argv


def test_a_venv_cook_prints_what_it_runs(invoke, ran, built):
    """The env line carries every switch, then the venv's python and the script."""
    code, out, _ = invoke("cook-with", "crewai", "--venv")
    assert code == 0
    printed = printed_argv(out)
    stack = registry.find("crewai")
    assert ran[-1] == [str(environ.venv_python(stack)), str(stack.script)]
    assert printed[-2:] == ran[-1]
    for key, value in environ.TELEMETRY_OFF.items():
        assert f"{key}={value}" in printed


def test_a_venv_cook_with_telemetry_prints_no_switch(invoke, ran, built):
    """--telemetry hands the defaults back, and the print says so."""
    _, out, _ = invoke("cook-with", "crewai", "--venv", "--telemetry")
    printed = printed_argv(out)
    assert not any(token.split("=")[0] in environ.TELEMETRY_OFF for token in printed)


def every_printed_argv(out):
    """Read back every command carbonara printed, in order."""
    blocks = out.split("carbonara: running\n")[1:]
    return [printed_argv("carbonara: running\n" + block) for block in blocks]


def test_a_locked_docker_cook_prints_the_relay_the_run_and_the_cleanup(
    invoke, ran, built
):
    """The printed lines, pasted in order, rebuild the lock, cook, and tidy up."""
    code, out, _ = invoke("cook-with", "crewai", "--docker")
    assert code == 0
    printed = every_printed_argv(out)
    # The network inspect answers 0 under the stub, so no create is printed.
    assert printed == ran[1:]
    assert [argv[:3] for argv in printed] == [
        ["docker", "run", "--detach"],
        ["docker", "network", "connect"],
        ["docker", "run", "--rm"],
        ["docker", "rm", "--force"],
    ]
    assert containers.NETWORK in printed[2]
    assert printed[-1][-1] == printed[0][printed[0].index("--name") + 1]


def test_an_open_docker_cook_prints_only_the_run(invoke, ran, built):
    """--telemetry needs no relay, so the print is the docker run alone."""
    code, out, _ = invoke("cook-with", "crewai", "--docker", "--telemetry")
    assert code == 0
    assert every_printed_argv(out) == ran
    assert ran[-1][:2] == ["docker", "run"]
    assert "--network" not in ran[-1]


def test_prep_docker_prints_the_build(invoke, ran):
    """The image build is a command too, and it is shown."""
    code, out, _ = invoke("prep", "crewai", "--docker")
    assert code == 0
    assert printed_argv(out) == ran[-1]
    assert ran[-1][:2] == ["docker", "build"]
