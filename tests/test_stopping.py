"""A signal stops a cook cleanly: the child first, then carbonara, in one line.

The child tests run real processes, since the claim is about what the operating
system delivers. A driver stands in for carbonara so the test process itself is
never signalled.
"""

import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from carbonara import cli, cli_cook_with, errors

SRC = Path(cli.__file__).resolve().parent.parent

#: The child: note its PID, then sleep until SIGINT, which it records.
CHILD = textwrap.dedent("""
    import pathlib, signal, sys, time
    here = pathlib.Path(sys.argv[1])
    def leave(signum, frame):
        (here / "child-got").write_text(signal.Signals(signum).name)
        sys.exit(0)
    signal.signal(signal.SIGINT, leave)
    (here / "child-pid").write_text(str(__import__("os").getpid()))
    time.sleep(60)
""")

#: The driver: carbonara's SIGTERM handler around wait_for, and its exit code.
DRIVER = textwrap.dedent("""
    import signal, sys
    from carbonara import cli, environ, errors
    signal.signal(signal.SIGTERM, cli.raise_stopped)
    try:
        environ.wait_for([sys.executable, "-c", sys.argv[1], sys.argv[2]])
    except errors.Stopped as stop:
        sys.exit(128 + stop.signum)
""")


def wait_until(path, seconds=10):
    """Return once path exists, or fail the test after the given seconds."""
    deadline = time.monotonic() + seconds
    while not path.exists():
        if time.monotonic() > deadline:
            pytest.fail(f"{path.name} never appeared")
        time.sleep(0.05)


def test_sigterm_stops_the_child_with_sigint_first(tmp_path):
    """SIGTERM on the driver reaches the child as SIGINT, and the child is gone."""
    driver = subprocess.Popen(
        [sys.executable, "-c", DRIVER, CHILD, str(tmp_path)],
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    wait_until(tmp_path / "child-pid")
    child = int((tmp_path / "child-pid").read_text())

    driver.send_signal(signal.SIGTERM)
    assert driver.wait(timeout=20) == 128 + signal.SIGTERM
    assert (tmp_path / "child-got").read_text() == "SIGINT"
    with pytest.raises(ProcessLookupError):
        os.kill(child, 0)


@pytest.mark.parametrize(
    ("raised", "line", "code"),
    [
        (KeyboardInterrupt(), "carbonara: stopped by Ctrl-C", 130),
        (errors.Stopped(signal.SIGTERM), "carbonara: stopped by SIGTERM", 143),
    ],
    ids=["ctrl-c", "sigterm"],
)
def test_a_stopped_cook_ends_on_one_line(invoke, monkeypatch, raised, line, code):
    """A signal ends the run through main: one line, the shell's code, no traceback."""

    def interrupted(stack, parsed):
        raise raised

    monkeypatch.setattr(cli_cook_with, "run", interrupted)
    got, out, err = invoke("cook-with", "crewai", "--venv")
    assert got == code
    assert err.strip() == line
    assert "Traceback" not in out + err


def test_main_puts_the_sigterm_handler_back(invoke, monkeypatch):
    """The handler lives only as long as the action, so nothing outlives a call."""
    monkeypatch.setattr(cli_cook_with, "run", lambda stack, parsed: None)
    before = signal.getsignal(signal.SIGTERM)
    invoke("cook-with", "crewai", "--venv")
    assert signal.getsignal(signal.SIGTERM) is before
