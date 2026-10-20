"""Docker mode: one image per stack, a locked network, and a relay to Ollama.

The dispatcher reaches Docker through the docker command alone. Every command
line is built by a pure function, so its shape is testable without a daemon.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

from . import environ
from .args import EXIT_ERROR

DOCKERFILE = Path(__file__).parent / "docker" / "Dockerfile"

# Internal, so a container on it has no route out. Only the relay joins it
# from the outside.
NETWORK = "carbonara-locked"

# socat 1.8.1.3, pinned by digest so the one thing allowed onto the locked
# network never changes under it.
RELAY_IMAGE = (
    "alpine/socat@sha256:"
    "fb3862c949af7c79996d0e514ee96128644d840835ed5368eeecb14a869de361"
)

# Ollama answers 403 to a Host header it does not recognise, which a plain
# name like "ollama" is. Names under .internal pass. host.docker.internal
# must never be used: Docker Desktop resolves it itself, past the relay.
RELAY_ALIAS = "ollama.internal"

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


def ollama_target():
    """Return the host and port Ollama is reached at from inside Docker.

    A loopback host means the machine Docker runs on, which a container calls
    host.docker.internal. Any other host is kept as it is.
    """
    parts = urlsplit(environ.ollama_base_url())
    host = parts.hostname or "127.0.0.1"
    if host in LOOPBACK:
        host = HOST_GATEWAY
    return host, parts.port or 11434


def ollama_url(telemetry=False):
    """Return the Ollama URL a stack container is handed.

    Locked, it reaches Ollama through the relay. Open, it goes direct.
    """
    host, port = ollama_target()
    if not telemetry:
        host = RELAY_ALIAS
    return f"http://{host}:{port}"


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


def network_argv():
    """Return the command that creates the locked network."""
    return ["docker", "network", "create", "--internal", NETWORK]


def relay_argv(name):
    """Return the command that starts a relay forwarding one port to Ollama.

    It starts on the default bridge, which can reach the host. It joins the
    locked network afterwards, through connect_argv().
    """
    host, port = ollama_target()
    return [
        "docker",
        "run",
        "--detach",
        "--rm",
        "--name",
        name,
        "--add-host",
        f"{HOST_GATEWAY}:host-gateway",
        RELAY_IMAGE,
        f"TCP-LISTEN:{port},fork,reuseaddr",
        f"TCP:{host}:{port}",
    ]


def connect_argv(name):
    """Return the command that puts the relay on the locked network."""
    return ["docker", "network", "connect", "--alias", RELAY_ALIAS, NETWORK, name]


def run_argv(stack, overrides=None, telemetry=False, tty=False):
    """Return the command that cooks this stack in a container.

    Locked unless telemetry is asked for. The switches in TELEMETRY_OFF and
    crewai's consent directory go in as well, so the network is a backstop
    rather than the only defence.
    """
    argv = ["docker", "run", "--rm"]
    if tty:
        argv += ["--interactive", "--tty"]

    environment = {}
    if telemetry:
        # Docker Desktop answers this name on its own. Linux needs it spelled out.
        argv += ["--add-host", f"{HOST_GATEWAY}:host-gateway"]
    else:
        argv += ["--network", NETWORK]
        environment.update(environ.TELEMETRY_OFF)
        environment["CREWAI_STORAGE_DIR"] = environ.CREWAI_STORAGE_NAME
        argv += [
            "--volume",
            f"{environ.crewai_state_dir()}:{CREWAI_STATE_IN_CONTAINER}",
        ]
    for key, value in (overrides or {}).items():
        if value is not None:
            environment[key] = str(value)
    environment["CARBONARA_OLLAMA_URL"] = ollama_url(telemetry)
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


def quietly(argv, what):
    """Print a docker command, run it for its effect, and report a failure.

    Returns True on success.
    """
    environ.print_command(argv)
    done = subprocess.run(argv, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        print(f"carbonara: could not {what}", file=sys.stderr)
        print(f"  {done.stderr.strip()}", file=sys.stderr)
    return done.returncode == 0


def ensure_network():
    """Create the locked network unless it is already there."""
    inspected = subprocess.run(
        ["docker", "network", "inspect", NETWORK], capture_output=True, check=False
    )
    if inspected.returncode == 0:
        return True
    return quietly(network_argv(), f"create the {NETWORK} network")


def cook(argv):
    """Print the stack's docker run, run it, and return its exit code."""
    environ.print_command(argv)
    return subprocess.run(argv, check=False).returncode


def run(stack, overrides=None, telemetry=False):
    """Cook this stack in a container, returning its exit code.

    A locked cook starts its own relay and removes it in a finally, so an
    interrupted cook leaves no container behind.
    """
    tty = sys.stdin.isatty() and sys.stdout.isatty()
    argv = run_argv(stack, overrides, telemetry=telemetry, tty=tty)
    if telemetry:
        return cook(argv)

    environ.decline_crewai_tracing()
    if not ensure_network():
        return EXIT_ERROR
    relay = f"carbonara-relay-{os.getpid()}"
    try:
        if not quietly(relay_argv(relay), "start the Ollama relay"):
            return EXIT_ERROR
        if not quietly(connect_argv(relay), f"put the relay on {NETWORK}"):
            return EXIT_ERROR
        return cook(argv)
    finally:
        remove = ["docker", "rm", "--force", relay]
        environ.print_command(remove)
        subprocess.run(remove, capture_output=True, check=False)
