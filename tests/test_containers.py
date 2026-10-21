"""Docker mode's command lines, pinned without a daemon.

Telemetry in a container is only as off as the argv says, so the shape of
each docker command is asserted here rather than trusted.
"""

import pytest

from carbonara import containers, environ, registry


@pytest.fixture
def crewai():
    """Return the crewai stack, the one that phones home hardest."""
    return registry.find("crewai")


def env_of(argv):
    """Return the --env pairs of a docker run argv as a dict."""
    pairs = [argv[i + 1] for i, token in enumerate(argv) if token == "--env"]
    return dict(pair.split("=", 1) for pair in pairs)


def test_a_locked_run_is_on_the_internal_network(crewai):
    """No --telemetry means the network with no route out."""
    argv = containers.run_argv(crewai)
    assert argv[argv.index("--network") + 1] == containers.NETWORK


def test_a_locked_run_reaches_ollama_through_the_relay(crewai, monkeypatch):
    """The stack is handed the relay's alias, never the host's own name."""
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    url = env_of(containers.run_argv(crewai))["CARBONARA_OLLAMA_URL"]
    assert url == "http://ollama.internal:11434"


def test_a_cook_sets_every_switch(crewai):
    """The lock is a backstop. The switches go in as they do in venv mode."""
    seen = env_of(containers.run_argv(crewai))
    for key, value in environ.TELEMETRY_OFF.items():
        assert seen[key] == value
    assert seen["CREWAI_STORAGE_DIR"] == environ.CREWAI_STORAGE_NAME


def test_a_cook_carries_the_crewai_consent(crewai):
    """The host's consent directory is mounted where crewai looks on Linux."""
    argv = containers.run_argv(crewai)
    mount = f"{environ.crewai_state_dir()}:{containers.CREWAI_STATE_IN_CONTAINER}"
    assert mount in argv


def test_telemetry_hands_back_the_defaults(crewai):
    """--telemetry sets no switch and mounts no consent, as in venv mode."""
    argv = containers.run_argv(crewai, telemetry=True)
    assert set(env_of(argv)).isdisjoint(environ.TELEMETRY_OFF)
    assert "CREWAI_STORAGE_DIR" not in env_of(argv)
    assert not any(containers.CREWAI_STATE_IN_CONTAINER in token for token in argv)


def test_telemetry_opens_the_network(crewai, monkeypatch):
    """--telemetry runs on the default network, straight to the host."""
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    argv = containers.run_argv(crewai, telemetry=True)
    assert "--network" not in argv
    url = env_of(argv)["CARBONARA_OLLAMA_URL"]
    assert url == "http://host.docker.internal:11434"


def test_an_open_cook_can_name_the_host_on_linux(crewai):
    """host.docker.internal is mapped explicitly, for Docker outside Desktop."""
    argv = containers.run_argv(crewai, telemetry=True)
    assert argv[argv.index("--add-host") + 1] == "host.docker.internal:host-gateway"


def test_the_network_is_internal():
    """Internal is the whole lock."""
    assert containers.network_argv() == [
        "docker",
        "network",
        "create",
        "--internal",
        containers.NETWORK,
    ]


def test_the_relay_alias_is_one_ollama_accepts():
    """Ollama answers 403 to a plain name. Docker Desktop hijacks the host's."""
    assert containers.RELAY_ALIAS.endswith((".internal", ".localhost"))
    assert containers.RELAY_ALIAS != "host.docker.internal"
    argv = containers.connect_argv("relay")
    assert argv[argv.index("--alias") + 1] == containers.RELAY_ALIAS
    assert containers.NETWORK in argv


def test_the_relay_forwards_one_port_to_the_host(monkeypatch):
    """A loopback OLLAMA_HOST is the host, which a container calls by name."""
    monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:4242")
    argv = containers.relay_argv("relay")
    assert argv[-2:] == [
        "TCP-LISTEN:4242,fork,reuseaddr",
        "TCP:host.docker.internal:4242",
    ]
    assert containers.RELAY_IMAGE in argv
    assert "@sha256:" in containers.RELAY_IMAGE


@pytest.mark.parametrize(
    "ollama_host", ["127.0.0.1:4242", "localhost:4242", "http://0.0.0.0:4242"]
)
def test_a_loopback_ollama_is_the_host(monkeypatch, ollama_host):
    """Loopback on the host is the host itself, seen from a container."""
    monkeypatch.setenv("OLLAMA_HOST", ollama_host)
    assert containers.ollama_target() == ("host.docker.internal", 4242)


def test_a_remote_ollama_is_kept_as_is(monkeypatch):
    """Only loopback is translated. A named host is reached by name."""
    monkeypatch.setenv("OLLAMA_HOST", "http://gpu-box:11434")
    assert containers.ollama_target() == ("gpu-box", 11434)


def test_overrides_cross_as_env_and_the_url_is_translated(crewai, monkeypatch):
    """CARBONARA_* overrides reach the container, but not the host's URL."""
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    argv = containers.run_argv(
        crewai,
        telemetry=True,
        overrides={
            "CARBONARA_ORDER": "eggs",
            "CARBONARA_MODEL": None,
            "CARBONARA_OLLAMA_URL": "http://127.0.0.1:11434",
        },
    )
    seen = env_of(argv)
    assert seen["CARBONARA_ORDER"] == "eggs"
    assert "CARBONARA_MODEL" not in seen
    assert seen["CARBONARA_OLLAMA_URL"] == "http://host.docker.internal:11434"


def test_the_script_is_mounted_read_only(crewai):
    """The image holds dependencies. The script comes from the package."""
    argv = containers.run_argv(crewai)
    assert f"{crewai.script}:{containers.SCRIPT_IN_CONTAINER}:ro" in argv
    assert argv[-3:] == [
        containers.image(crewai),
        "python",
        containers.SCRIPT_IN_CONTAINER,
    ]


@pytest.mark.parametrize(
    "pinned, name", [(True, "requirements-pinned.txt"), (False, "requirements.txt")]
)
def test_the_build_follows_the_stack(crewai, pinned, name):
    """The Python version and requirements come from the stack, as for a venv."""
    argv = containers.build_argv(crewai, pinned=pinned)
    assert f"PYTHON={crewai.python_version}" in argv
    assert f"REQUIREMENTS={name}" in argv
    assert argv[argv.index("-t") + 1] == "carbonara-crewai"
    assert argv[-1] == str(crewai.directory)


def test_the_dockerfile_ships():
    """A pipx install needs the Dockerfile beside the stacks."""
    assert containers.DOCKERFILE.is_file()


#: Captured at import, before the offline fixture replaces it.
CHECK_DOCKER = containers.check_docker


@pytest.fixture
def envs(monkeypatch):
    """Stub every docker call and hand back the environment each was given."""
    seen = []

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(argv, **kwargs):
        seen.append(kwargs.get("env"))
        return Completed()

    def fake_wait_for(argv, **options):
        seen.append(options.get("env"))
        return 0

    monkeypatch.setattr(containers.subprocess, "run", fake_run)
    monkeypatch.setattr(environ, "wait_for", fake_wait_for)
    monkeypatch.setattr(containers.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.delenv("DOCKER_CLI_HINTS", raising=False)
    return seen


def hints_of(envs):
    """Return the DOCKER_CLI_HINTS each docker call ran with."""
    return [env and env.get("DOCKER_CLI_HINTS") for env in envs]


def test_every_docker_call_hides_the_hints(invoke, envs, crewai):
    """A locked cook, a clean, and the probes all run with the hints off."""
    assert invoke("cook-with", "crewai", "--docker")[0] == 0
    assert invoke("clean", "crewai", "--docker")[0] == 0
    CHECK_DOCKER()
    containers.build(crewai)
    assert len(envs) > 8
    assert set(hints_of(envs)) == {"false"}


def test_a_hint_asked_for_stays(invoke, envs, monkeypatch):
    """DOCKER_CLI_HINTS already set is the user's, and it wins."""
    monkeypatch.setenv("DOCKER_CLI_HINTS", "true")
    assert invoke("cook-with", "crewai", "--docker")[0] == 0
    assert set(hints_of(envs)) == {"true"}


def test_the_hint_switch_is_never_printed(invoke, envs):
    """Rule 4's one exception: the switch is set, not shown."""
    _, out, _ = invoke("cook-with", "crewai", "--docker")
    assert "carbonara: running" in out
    assert "DOCKER_CLI_HINTS" not in out


def test_a_terminal_run_takes_a_tty_and_never_stdin(crewai):
    """--interactive puts the terminal in raw mode, and Ctrl-C bypasses carbonara."""
    argv = containers.run_argv(crewai, tty=True)
    assert "--tty" in argv
    assert "--interactive" not in argv


def test_a_run_off_a_terminal_takes_neither(crewai):
    """Piped, the stack gets no tty and no stdin."""
    argv = containers.run_argv(crewai)
    assert "--tty" not in argv
    assert "--interactive" not in argv
