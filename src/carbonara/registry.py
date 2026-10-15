"""The four agent stacks, described as data the dispatcher reads.

Nothing here imports a stack. A stack is a directory of files handed to
another interpreter, and treating one as an importable module would put
`crewai` back inside a 3.14 process, which is exactly what this tool exists
to avoid.
"""

from pathlib import Path
from typing import NamedTuple

STACKS_DIR = Path(__file__).parent / "stacks"

#: The model every stack talks to, and the one readiness checks look for.
DEFAULT_MODEL = "hf.co/CohereLabs/tiny-aya-global-GGUF:Q4_K_M"

SUMMARIES = {
    "no-framework": "Plain Python. A prompt and a registry.",
    "crewai": "Role-based agents with a crew and tasks.",
    "langgraph": "A state graph, nodes and edges.",
    "smolagents": "Minimal agents over LiteLLM.",
}

#: Presentation order. The no-framework stack leads because it is the one that
#: shows the mechanism with nothing in front of it.
NAMES = ("no-framework", "crewai", "langgraph", "smolagents")

#: The stacks that reach the network on their own account, run with the
#: frameworks' own defaults. Measured, not read: every hostname a cook looks up
#: is logged, and docs/CALLS-HOME.md holds the runs. crewai sends its own
#: telemetry. smolagents' call comes from LiteLLM, a library underneath it.
#: langgraph could, once LangSmith tracing is turned on, and is not counted.
PHONES_HOME = frozenset({"crewai", "smolagents"})


class Stack(NamedTuple):
    """One agent stack: where its files are and which interpreter it wants."""

    name: str
    summary: str
    directory: Path

    @property
    def script(self):
        """Return the path to this stack's demo script."""
        return self.directory / "carbonara.py"

    @property
    def python_version(self):
        """Return the Python version this stack pins, as a string like "3.12"."""
        return (self.directory / "python-version").read_text().strip()

    @property
    def phones_home(self):
        """Report whether this stack reaches the network by default."""
        return self.name in PHONES_HOME

    def requirements(self, pinned=True):
        """Return the requirements file to install from."""
        name = "requirements-pinned.txt" if pinned else "requirements.txt"
        return self.directory / name


def stacks():
    """Return every stack, in presentation order."""
    return [Stack(name, SUMMARIES[name], STACKS_DIR / name) for name in NAMES]


def find(name):
    """Return the stack with this name, or None if there is no such stack."""
    if name not in SUMMARIES:
        return None
    return Stack(name, SUMMARIES[name], STACKS_DIR / name)
