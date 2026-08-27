"""Shared fixtures.

The runner is the one that matters. Exit codes arrive two ways: 0 and 1 return
through main(), while argparse's 2 and the version action's 0 unwind as
SystemExit. One helper catches both so every test compares the same thing.
"""

import sys

import pytest

from carbonara import cli, environ, registry

#: Captured before the offline fixture replaces it, for the one test that
#: needs the real thing.
REAL_VENVS_ROOT = environ.venvs_root


@pytest.fixture
def invoke(monkeypatch, capsys):
    """Return a callable that runs carbonara and hands back (code, out, err)."""

    def run(*arguments):
        monkeypatch.setattr(sys, "argv", ["carbonara", *arguments])
        try:
            code = cli.main()
        except SystemExit as stop:
            code = 0 if stop.code is None else stop.code
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return run


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    """Keep the suite off the network and out of the real environment tree."""
    monkeypatch.setattr(environ, "installed_models", lambda: {registry.DEFAULT_MODEL})
    monkeypatch.setattr(environ, "venvs_root", lambda: tmp_path / "venvs")
    monkeypatch.setattr(environ, "crewai_state_dir", lambda *a, **k: tmp_path / "state")


@pytest.fixture
def real_venvs_root():
    """Return the unpatched venvs_root, which the offline fixture replaces."""
    return REAL_VENVS_ROOT
