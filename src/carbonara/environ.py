"""Interpreter discovery, per-stack virtual environments, and readiness.

Every function here works through the filesystem or a subprocess. Nothing in
this module imports anything a stack depends on.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import NamedTuple

from . import registry

WINDOWS = os.name == "nt"

# Every phone-home switch the four stacks honour, set to off. carbonara sets
# these before it runs anything, and --telemetry leaves them unset so the
# frameworks behave as their own documentation says.
TELEMETRY_OFF = {
    "CREWAI_DISABLE_TELEMETRY": "true",
    "CREWAI_DISABLE_TRACKING": "true",
    "OTEL_SDK_DISABLED": "true",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "LANGCHAIN_TRACING_V2": "false",
    "LANGSMITH_TRACING": "false",
}

# crewai files its consent under the basename of the working directory unless
# CREWAI_STORAGE_DIR says otherwise, so without this the question is asked
# again from every new directory and never stays answered.
CREWAI_STORAGE_NAME = "carbonara"


class Check(NamedTuple):
    """The result of a readiness check, with the command that repairs it."""

    ok: bool
    problem: str = ""
    fix: str = ""


def venvs_root():
    """Return the directory holding every stack's virtual environment."""
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home) if data_home else Path.home() / ".local" / "share"
    return base / "carbonara" / "venvs"


def venv_dir(stack):
    """Return the virtual environment directory for one stack."""
    return venvs_root() / stack.name


def venv_python(stack):
    """Return the interpreter inside one stack's virtual environment."""
    bindir = "Scripts" if WINDOWS else "bin"
    return venv_dir(stack) / bindir / ("python.exe" if WINDOWS else "python")


def is_built(stack):
    """Report whether this stack's virtual environment exists and has a Python."""
    return venv_python(stack).exists()


def pyenv_interpreter(version):
    """Return the interpreter pyenv holds for a version like "3.12", or None.

    `pyenv prefix` resolves a partial version and answers from what is actually
    installed, which is what makes it worth asking separately from PATH.
    """
    if shutil.which("pyenv") is None:
        return None
    try:
        result = subprocess.run(
            ["pyenv", "prefix", version],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    candidate = Path(result.stdout.strip()) / "bin" / "python"
    return str(candidate) if candidate.exists() else None


def find_interpreter(version):
    """Return a usable interpreter for a version like "3.12", or None.

    Three places are asked, because each misses on its own. A pyenv shim is
    version-gated: `python3.12` sits on PATH and still refuses to run when the
    directory's `.python-version` names something else, so PATH reports absent
    for an interpreter that is installed. pyenv itself answers from what is
    installed. And a pipx install can sit on an interpreter PATH never names.

    Every candidate is run and asked what version it is, so a shim that
    resolves somewhere unexpected is caught rather than trusted.
    """
    candidates = [
        shutil.which(f"python{version}"),
        pyenv_interpreter(version),
        sys.executable,
    ]

    for candidate in filter(None, candidates):
        try:
            result = subprocess.run(
                [candidate, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0 and result.stdout.strip() == version:
            return candidate
    return None


def check_interpreter(stack):
    """Check that the interpreter this stack pins is installed and runnable."""
    version = stack.python_version
    if find_interpreter(version) is None:
        return Check(
            False,
            f"no working Python {version} for the {stack.name} stack",
            f"pyenv install {version}",
        )
    return Check(True)


def ollama_base_url():
    """Return the base URL of the Ollama server, honouring OLLAMA_HOST."""
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    if "://" not in host:
        host = f"http://{host}"
    return host.rstrip("/")


def installed_models():
    """Return the model names Ollama reports, or None if it is unreachable."""
    url = f"{ollama_base_url()}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.load(response)
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None
    return {model.get("name", "") for model in payload.get("models", [])}


def check_ollama(model=registry.DEFAULT_MODEL):
    """Check that Ollama is reachable and has the model pulled."""
    models = installed_models()
    if models is None:
        return Check(
            False,
            f"Ollama is not reachable at {ollama_base_url()}",
            "ollama serve",
        )
    if model not in models:
        return Check(
            False, f"Ollama does not have {model} pulled", f"ollama pull {model}"
        )
    return Check(True)


def build(stack, pinned=True, stream=None):
    """Create this stack's virtual environment and install its requirements.

    Returns True on success. Progress goes to `stream`, defaulting to stdout.
    """
    stream = stream or sys.stdout
    interpreter = find_interpreter(stack.python_version)
    if interpreter is None:
        return False

    target = venv_dir(stack)
    target.parent.mkdir(parents=True, exist_ok=True)

    print(f"  building {target} on Python {stack.python_version}", file=stream)
    created = subprocess.run([interpreter, "-m", "venv", str(target)], check=False)
    if created.returncode != 0:
        return False

    python = str(venv_python(stack))
    subprocess.run(
        [python, "-m", "pip", "install", "--upgrade", "--quiet", "pip"], check=False
    )

    requirements = stack.requirements(pinned=pinned)
    print(f"  installing from {requirements.name}", file=stream)
    installed = subprocess.run(
        [python, "-m", "pip", "install", "-r", str(requirements)], check=False
    )
    return installed.returncode == 0


def crewai_state_dir(storage_name=CREWAI_STORAGE_NAME):
    """Return the directory crewai keeps its consent file in.

    This mirrors what appdirs resolves for the same name. carbonara imports no
    framework and so cannot ask appdirs itself.
    """
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / storage_name
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home) if data_home else Path.home() / ".local" / "share"
    return base / storage_name


def decline_crewai_tracing(storage_name=CREWAI_STORAGE_NAME):
    """Record a declined trace consent, without overwriting an answer already there.

    No environment variable can turn crewai's tracing off. CREWAI_TRACING_ENABLED
    is read as `in ("true", "1")`, so it only ever turns tracing on, and the
    consent file is the sole control. An answer already in the file is left
    alone, so a deliberate yes survives.

    Returns True when this call wrote the decline.
    """
    path = crewai_state_dir(storage_name) / ".crewai_user.json"
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            return False
    if "trace_consent" in data:
        return False

    # crewai tests this with `is not False`, so it must be a literal JSON
    # false. A null in that slot enables tracing.
    data["trace_consent"] = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
    except OSError:
        return False
    return True


def run(stack, overrides=None, telemetry=False):
    """Run this stack's demo in its own environment, returning its exit code."""
    environment = dict(os.environ)
    if not telemetry:
        environment.update(TELEMETRY_OFF)
        environment["CREWAI_STORAGE_DIR"] = CREWAI_STORAGE_NAME
        decline_crewai_tracing()
    for key, value in (overrides or {}).items():
        if value is not None:
            environment[key] = str(value)
    completed = subprocess.run(
        [str(venv_python(stack)), str(stack.script)], env=environment, check=False
    )
    return completed.returncode


def report(check):
    """Print a readiness failure and the command that repairs it.

    No usage line goes with it. The command line was read fine and something
    the run needed was not there, so usage would answer a question nobody
    asked.
    """
    print(f"carbonara: {check.problem}", file=sys.stderr)
    print(f"  try: {check.fix}", file=sys.stderr)
