"""Docker mode: one image per stack, run on Docker's default network.

The dispatcher reaches Docker through the docker command alone. Every command
line is built by a pure function, so its shape is testable without a daemon.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

from . import environ

DOCKERFILE = Path(__file__).parent / "docker" / "Dockerfile"

# What a container calls the machine Docker runs on.
HOST_GATEWAY = "host.docker.internal"
LOOPBACK = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}

SCRIPT_IN_CONTAINER = "/kitchen/carbonara.py"

# Where crewai_state_dir() resolves on Linux for root, so the consent file
# written on the host is the one crewai reads in the container.
CREWAI_STATE_IN_CONTAINER = "/root/.local/share/carbonara"


def image(stack):
    """Return the image tag for this stack."""
    return f"carbonara-{stack.name}"


def ollama_url():
    """Return the Ollama URL a stack container is handed.

    A loopback host means the machine Docker runs on, which a container calls
    host.docker.internal. Any other host is kept as it is.
    """
    parts = urlsplit(environ.ollama_base_url())
    host = parts.hostname or "127.0.0.1"
    if host in LOOPBACK:
        host = HOST_GATEWAY
    return f"http://{host}:{parts.port or 11434}"


def build_argv(stack, pinned=True):
    """Return the command that builds this stack's image."""
    return [
        "docker",
        "build",
        "-f",
        str(DOCKERFILE),
        "--build-arg",
        f"PYTHON={stack.python_version}",
        "--build-arg",
        f"REQUIREMENTS={stack.requirements(pinned=pinned).name}",
        "-t",
        image(stack),
        str(stack.directory),
    ]


def run_argv(stack, overrides=None, telemetry=False, tty=False):
    """Return the command that cooks this stack in a container.

    Telemetry is handled as in venv mode: the switches in TELEMETRY_OFF, and
    crewai's consent directory, unless telemetry is asked for.
    """
    argv = ["docker", "run", "--rm"]
    if tty:
        argv += ["--interactive", "--tty"]
    # Docker Desktop answers this name on its own. Linux needs it spelled out.
    argv += ["--add-host", f"{HOST_GATEWAY}:host-gateway"]

    environment = {}
    if not telemetry:
        environment.update(environ.TELEMETRY_OFF)
        environment["CREWAI_STORAGE_DIR"] = environ.CREWAI_STORAGE_NAME
        argv += [
            "--volume",
            f"{environ.crewai_state_dir()}:{CREWAI_STATE_IN_CONTAINER}",
        ]
    for key, value in (overrides or {}).items():
        if value is not None:
            environment[key] = str(value)
    environment["CARBONARA_OLLAMA_URL"] = ollama_url()
    for key, value in environment.items():
        argv += ["--env", f"{key}={value}"]

    argv += [
        "--volume",
        f"{stack.script}:{SCRIPT_IN_CONTAINER}:ro",
        image(stack),
        "python",
        SCRIPT_IN_CONTAINER,
    ]
    return argv


def check_docker():
    """Check that the docker command exists and its daemon answers."""
    if shutil.which("docker") is None:
        return environ.Check(
            False, "the docker command is not on PATH", "install Docker Desktop"
        )
    try:
        answered = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=20, check=False
        )
    except subprocess.TimeoutExpired:
        answered = None
    if answered is None or answered.returncode != 0:
        return environ.Check(False, "Docker is not running", "start Docker Desktop")
    return environ.Check(True)


def is_built(stack):
    """Report whether this stack's image exists."""
    inspected = subprocess.run(
        ["docker", "image", "inspect", image(stack)],
        capture_output=True,
        check=False,
    )
    return inspected.returncode == 0


def build(stack, pinned=True):
    """Build this stack's image. Returns True on success."""
    print(f"  building {image(stack)} on Python {stack.python_version}")
    argv = build_argv(stack, pinned)
    environ.print_command(argv)
    return subprocess.run(argv, check=False).returncode == 0


def run(stack, overrides=None, telemetry=False):
    """Cook this stack in a container, returning its exit code."""
    if not telemetry:
        environ.decline_crewai_tracing()
    tty = sys.stdin.isatty() and sys.stdout.isatty()
    argv = run_argv(stack, overrides, telemetry=telemetry, tty=tty)
    environ.print_command(argv)
    return subprocess.run(argv, check=False).returncode
