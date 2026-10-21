"""The three kinds of failure, each reported its own way.

A grammar error carries the usage line. A readiness failure is found before
the first write and carries none. A runtime failure stops a run partway.
"""

import subprocess

import pytest

from carbonara import containers, environ
from carbonara.cli import EXIT_ERROR


def test_a_readiness_failure_names_the_fix_and_no_usage(invoke, monkeypatch):
    """No Ollama: the problem and its repair, with no usage line."""
    monkeypatch.setattr(environ, "installed_models", lambda: None)
    code, _, err = invoke("cook-with", "crewai", "--venv")
    assert code == EXIT_ERROR
    assert err.startswith("carbonara: Ollama is not reachable at ")
    assert "\n  try: ollama serve\n" in err
    assert "Usage:" not in err


def test_no_docker_is_a_readiness_failure(invoke, monkeypatch):
    """Under --docker, a stopped Docker is found before anything is built."""
    monkeypatch.setattr(
        containers,
        "check_docker",
        lambda: environ.Check(False, "Docker is not running", "start Docker Desktop"),
    )
    code, _, err = invoke("prep", "crewai", "--docker")
    assert code == EXIT_ERROR
    assert err == "carbonara: Docker is not running\n  try: start Docker Desktop\n"


def test_a_failed_build_is_a_runtime_failure(invoke, monkeypatch):
    """The interpreter was there and the install broke partway."""
    monkeypatch.setattr(environ, "find_interpreter", lambda version: "/bin/python")
    monkeypatch.setattr(environ, "build", lambda stack, pinned=True: False)
    code, out, err = invoke("prep", "crewai", "--venv")
    assert code == EXIT_ERROR
    assert "prepping crewai" in out
    assert err == "carbonara: could not build the crewai environment\n"


@pytest.fixture
def refusing(monkeypatch):
    """Stub docker so the relay refuses to start, recording every argv."""
    ran = []

    class Completed:
        def __init__(self, returncode, stderr=""):
            self.returncode = returncode
            self.stderr = stderr

    def fake_run(argv, **kwargs):
        ran.append(argv)
        if argv[:3] == ["docker", "run", "--detach"]:
            return Completed(1, "Error response from daemon: port taken")
        return Completed(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(containers, "is_built", lambda stack: True)
    return ran


def test_a_relay_that_will_not_start_is_still_removed(invoke, refusing):
    """The raise leaves through the finally, so no relay container is left."""
    code, out, err = invoke("cook-with", "crewai", "--docker")
    assert code == EXIT_ERROR
    assert "could not start the Ollama relay\n  Error response" in err
    assert refusing[-1][:3] == ["docker", "rm", "--force"]
    assert not any(argv[:3] == ["docker", "run", "--rm"] for argv in refusing)
    assert out.rstrip().endswith(f"  docker rm \\\n    --force {refusing[-1][-1]}")
