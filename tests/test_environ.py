"""Interpreter discovery, environment paths, and the readiness checks."""

import sys
from pathlib import Path

from carbonara import environ, registry

RUNNING = f"{sys.version_info.major}.{sys.version_info.minor}"


def test_finds_the_interpreter_it_is_running_on():
    """Discovery is asked for a version that certainly exists."""
    assert environ.find_interpreter(RUNNING) is not None


def test_a_version_nobody_has_is_not_invented():
    """Discovery reports absence rather than handing back the wrong Python."""
    assert environ.find_interpreter("2.3") is None


def test_a_named_interpreter_is_run_before_it_is_trusted(monkeypatch):
    """A name on PATH is not a working interpreter.

    A pyenv shim answers to its name and still refuses to run, so a candidate
    that cannot report its own version is discarded rather than returned.
    """
    monkeypatch.setattr(environ.shutil, "which", lambda name: "/nonexistent/python9.9")
    monkeypatch.setattr(environ, "pyenv_interpreter", lambda version: None)
    assert environ.find_interpreter("9.9") is None


def test_environments_follow_xdg_data_home(monkeypatch, tmp_path, real_venvs_root):
    """XDG_DATA_HOME moves the environment tree, and nothing else does."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert real_venvs_root() == tmp_path / "carbonara" / "venvs"


def test_environments_default_under_local_share(monkeypatch, real_venvs_root):
    """With no XDG_DATA_HOME set, the tree sits under ~/.local/share."""
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    expected = Path.home() / ".local" / "share" / "carbonara" / "venvs"
    assert real_venvs_root() == expected


def test_an_unbuilt_stack_reports_unbuilt():
    """is_built() answers from the filesystem, not from a cache."""
    assert environ.is_built(registry.find("crewai")) is False


def test_ollama_host_gains_a_scheme(monkeypatch):
    """OLLAMA_HOST is commonly bare host:port, which urllib will not take."""
    monkeypatch.setenv("OLLAMA_HOST", "10.0.0.4:11434")
    assert environ.ollama_base_url() == "http://10.0.0.4:11434"


def test_an_unreachable_ollama_names_its_fix(monkeypatch):
    """A readiness failure carries the command that repairs it."""
    monkeypatch.setattr(environ, "installed_models", lambda: None)
    check = environ.check_ollama()
    assert check.ok is False
    assert check.fix == "ollama serve"


def test_a_missing_model_names_the_pull(monkeypatch):
    """Reaching Ollama is not the same as having the model."""
    monkeypatch.setattr(environ, "installed_models", lambda: {"something-else"})
    check = environ.check_ollama(registry.DEFAULT_MODEL)
    assert check.ok is False
    assert check.fix == f"ollama pull {registry.DEFAULT_MODEL}"


def test_overrides_drop_the_unset(monkeypatch):
    """A flag nobody passed must not reach the stack as the string "None"."""
    from carbonara.cli_cook_with import overrides

    class Args:
        order = "feed six"
        model = None
        temperature = 0.8
        stream_delay = None

    collected = overrides(Args())
    assert collected["CARBONARA_ORDER"] == "feed six"
    assert collected["CARBONARA_MODEL"] is None
