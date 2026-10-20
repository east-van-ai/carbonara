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


def test_a_cook_sets_every_switch(crewai):
    """Without --telemetry, the switches go in as they do in venv mode."""
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


@pytest.mark.parametrize("telemetry", [False, True])
def test_a_cook_is_on_the_default_network(crewai, telemetry):
    """No network is named. The locked network is a later release."""
    assert "--network" not in containers.run_argv(crewai, telemetry=telemetry)


def test_a_cook_can_name_the_host_on_linux(crewai):
    """host.docker.internal is mapped explicitly, for Docker outside Desktop."""
    argv = containers.run_argv(crewai)
    assert argv[argv.index("--add-host") + 1] == "host.docker.internal:host-gateway"


@pytest.mark.parametrize(
    "ollama_host", ["127.0.0.1:4242", "localhost:4242", "http://0.0.0.0:4242"]
)
def test_a_loopback_ollama_is_the_host(monkeypatch, ollama_host):
    """Loopback on the host is the host itself, seen from a container."""
    monkeypatch.setenv("OLLAMA_HOST", ollama_host)
    assert containers.ollama_url() == "http://host.docker.internal:4242"


def test_a_remote_ollama_is_kept_as_is(monkeypatch):
    """Only loopback is translated. A named host is reached by name."""
    monkeypatch.setenv("OLLAMA_HOST", "http://gpu-box:11434")
    assert containers.ollama_url() == "http://gpu-box:11434"


def test_overrides_cross_as_env_and_the_url_is_translated(crewai, monkeypatch):
    """CARBONARA_* overrides reach the container, but not the host's URL."""
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    argv = containers.run_argv(
        crewai,
        {
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
