"""The four stacks, and the boundary that keeps them out of this interpreter."""

import ast
from pathlib import Path

import pytest

from carbonara import registry

DISPATCHER = Path(registry.__file__).parent


@pytest.fixture(params=registry.NAMES)
def stack(request):
    """Yield each stack in turn."""
    return registry.find(request.param)


def test_every_stack_is_listed():
    """The presentation order and the summaries describe the same four stacks."""
    assert set(registry.NAMES) == set(registry.SUMMARIES)
    assert len(registry.NAMES) == 4


def test_unknown_stack_is_none():
    """A name that is not a stack resolves to None rather than a broken Stack."""
    assert registry.find("nosuch") is None


def test_stack_files_are_present(stack):
    """Each stack ships a script, both requirements files, and a version."""
    assert stack.script.is_file()
    assert stack.requirements(pinned=True).is_file()
    assert stack.requirements(pinned=False).is_file()
    assert stack.python_version.count(".") == 1


def test_crewai_is_the_one_on_312():
    """The interpreter split is the whole reason this tool exists. Pin it."""
    versions = {s.name: s.python_version for s in registry.stacks()}
    assert versions["crewai"] == "3.12"
    assert {v for n, v in versions.items() if n != "crewai"} == {"3.14"}


def test_stack_scripts_read_the_environment(stack):
    """Every stack takes its model, temperature, and order from CARBONARA_*.

    The CLI sets these across a subprocess boundary and cannot set them any
    other way, so a stack that stops reading them goes quietly deaf.
    """
    source = stack.script.read_text()
    for name in (
        "CARBONARA_MODEL",
        "CARBONARA_TEMPERATURE",
        "CARBONARA_ORDER",
        "CARBONARA_OLLAMA_URL",
    ):
        assert f'os.environ.get("{name}"' in source


def test_stack_scripts_hardcode_no_ollama_url(stack):
    """The Ollama URL appears once, as the default of CARBONARA_OLLAMA_URL.

    A second copy is a call that ignores OLLAMA_HOST, and in a locked
    container a call that reaches nothing.
    """
    lines = [line for line in stack.script.read_text().splitlines() if "11434" in line]
    assert len(lines) == 1
    assert "CARBONARA_OLLAMA_URL" in lines[0]


def test_stack_scripts_call_ollama_through_a_client(stack):
    """The module-level ollama.chat reads OLLAMA_HOST, never the URL it is given."""
    assert "ollama.chat(" not in stack.script.read_text()


def test_stack_scripts_keep_their_defaults(stack):
    """A stack still runs on its own, with nothing set. That is the demo."""
    source = stack.script.read_text()
    assert f'"{registry.DEFAULT_MODEL}"' in source
    assert '"make me a carbonara"' in source


def test_the_dispatcher_imports_no_stack():
    """No module in the dispatcher may import from stacks.

    Crossing that line puts a framework back inside this interpreter, which is
    exactly the conflict the whole design exists to avoid.
    """
    for module in DISPATCHER.glob("*.py"):
        tree = ast.parse(module.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert "stacks" not in (node.module or ""), module.name
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert "stacks" not in alias.name, module.name


def test_no_stack_imports_carbonara_or_another_stack(stack):
    """The four stay independent, which is what makes them comparable.

    Factoring their shared parts into a common module is the obvious tidy and
    would destroy the comparison.
    """
    tree = ast.parse(stack.script.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)

    # A stack's name is its framework's package name, so importing its own is
    # the whole point. Importing a sibling's is the violation.
    siblings = set(registry.NAMES) - {stack.name}
    assert "carbonara" not in imported
    assert imported.isdisjoint(siblings)


#: Tools that belong to a development venv, never to a stack. One leaking into
#: a pinned set means the set was frozen from the wrong venv.
DEVELOPER_TOOLS = {"black", "ruff", "pytest", "pip"}


def test_pinned_sets_hold_no_developer_tool(stack):
    """A pin frozen from a development venv ships its formatter to every user."""
    lines = stack.requirements(pinned=True).read_text().splitlines()
    names = {line.split("==")[0].lower() for line in lines if "==" in line}
    assert names.isdisjoint(DEVELOPER_TOOLS)


def test_pinned_sets_say_when_they_were_tested(stack):
    """The header dates the set, so a stale pin is visible at a glance."""
    first = stack.requirements(pinned=True).read_text().splitlines()[0]
    assert first.startswith("# tested on ")


@pytest.mark.parametrize("pinned", [True, False])
def test_requirements_end_with_a_newline(stack, pinned):
    """A missing final newline glues the next file's first line onto the last."""
    assert stack.requirements(pinned=pinned).read_text().endswith("\n")
