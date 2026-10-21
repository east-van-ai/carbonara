"""clean removes one stack's station and nothing beside it.

The venv side runs for real against the offline fixture's scratch venvs root.
The Docker side stubs subprocess.run, since the suite stays off Docker.
"""

import shlex
import subprocess

import pytest

from carbonara import containers, environ, registry
from carbonara.cli import EXIT_ERROR, EXIT_OK


def make_venv(stack):
    """Lay down a stand-in venv for this stack, with one file inside."""
    path = environ.venv_dir(stack)
    (path / "bin").mkdir(parents=True)
    (path / "bin" / "python").write_text("")
    return path


@pytest.fixture
def docker(monkeypatch):
    """Stub docker: an image and a network, each present unless told otherwise.

    Hands back the state to adjust, and every argv run is recorded in it.
    """
    state = {"image": True, "network": True, "fail": set(), "ran": []}

    class Completed:
        def __init__(self, returncode, stderr=""):
            self.returncode = returncode
            self.stderr = stderr

    def fake_run(argv, **kwargs):
        state["ran"].append(argv)
        if argv[:3] == ["docker", "network", "inspect"]:
            return Completed(0 if state["network"] else 1)
        if argv[2] == "rm" and argv[1] in state["fail"]:
            return Completed(1, "Error response from daemon: in use")
        return Completed(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(containers, "is_built", lambda stack: state["image"])
    return state


def removals(state):
    """Return every argv run that removes something."""
    return [argv for argv in state["ran"] if "rm" in argv]


def printed(out):
    """Read back every command carbonara printed, as a shell would."""
    blocks = out.split("carbonara: running\n")[1:]
    return [shlex.split(block.splitlines()[0]) for block in blocks]


def test_a_built_venv_is_removed_and_its_siblings_stay(invoke):
    """clean removes the named stack's venv and no other."""
    gone = make_venv(registry.find("crewai"))
    kept = make_venv(registry.find("langgraph"))
    code, out, _ = invoke("clean", "crewai", "--venv")
    assert code == EXIT_OK
    assert f"removed {gone}" in out
    assert not gone.exists()
    assert (kept / "bin" / "python").exists()


def test_cleaning_twice_is_not_a_failure(invoke):
    """Something already gone is reported, exit 0, every time."""
    make_venv(registry.find("crewai"))
    invoke("clean", "crewai", "--venv")
    for _ in range(2):
        code, out, _ = invoke("clean", "crewai", "--venv")
        assert code == EXIT_OK
        assert "nothing to clean" in out


def test_a_symlink_in_the_venvs_place_is_refused(invoke, tmp_path):
    """carbonara never makes a link there, so it stays, and so does its target."""
    target = tmp_path / "elsewhere"
    target.mkdir()
    (target / "keep").write_text("")
    link = environ.venv_dir(registry.find("crewai"))
    link.parent.mkdir(parents=True)
    link.symlink_to(target)
    code, _, err = invoke("clean", "crewai", "--venv")
    assert code == EXIT_ERROR
    assert "stays" in err
    assert link.is_symlink()
    assert (target / "keep").exists()


def test_the_crewai_consent_file_survives(invoke):
    """clean crewai leaves crewai's consent file alone."""
    make_venv(registry.find("crewai"))
    environ.decline_crewai_tracing()
    consent = environ.crewai_state_dir() / ".crewai_user.json"
    assert consent.exists()
    code, _, _ = invoke("clean", "crewai", "--venv")
    assert code == EXIT_OK
    assert consent.exists()


def test_docker_removes_the_image_then_the_network(invoke, docker):
    """Each removal is printed exactly as it is run, image first."""
    code, out, _ = invoke("clean", "crewai", "--docker")
    assert code == EXIT_OK
    expected = [
        ["docker", "image", "rm", "carbonara-crewai"],
        ["docker", "network", "rm", containers.NETWORK],
    ]
    assert removals(docker) == expected
    assert printed(out) == expected


def test_docker_with_nothing_there_removes_nothing(invoke, docker):
    """No image and no network: two reports, no rm, exit 0."""
    docker["image"] = False
    docker["network"] = False
    code, out, _ = invoke("clean", "crewai", "--docker")
    assert code == EXIT_OK
    assert removals(docker) == []
    assert out.count("nothing to clean") == 2


def test_a_refused_image_still_tries_the_network(invoke, docker):
    """One refusal does not hide the other, and the command exits 1."""
    docker["fail"] = {"image"}
    code, _, err = invoke("clean", "crewai", "--docker")
    assert code == EXIT_ERROR
    assert "could not remove carbonara-crewai" in err
    assert ["docker", "network", "rm", containers.NETWORK] in removals(docker)


def test_two_refusals_are_both_reported(invoke, docker):
    """The image and the network each name their own refusal, exit 1."""
    docker["fail"] = {"image", "network"}
    code, _, err = invoke("clean", "crewai", "--docker")
    assert code == EXIT_ERROR
    assert err.splitlines() == [
        "carbonara: could not remove carbonara-crewai",
        "  Error response from daemon: in use",
        f"carbonara: could not remove the {containers.NETWORK} network",
        "  Error response from daemon: in use",
    ]


def test_the_relay_image_is_never_removed(invoke, docker):
    """The relay image is pinned by digest, so clean leaves it."""
    invoke("clean", "crewai", "--docker")
    assert removals(docker)
    assert not any(containers.RELAY_IMAGE in argv for argv in docker["ran"])


def test_docker_clean_leaves_the_venv(invoke, docker):
    """--docker touches Docker only, as in prep."""
    path = make_venv(registry.find("crewai"))
    code, _, _ = invoke("clean", "crewai", "--docker")
    assert code == EXIT_OK
    assert path.exists()
