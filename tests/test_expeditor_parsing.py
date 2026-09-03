"""The expeditor's plan parser, in the two stacks that have one.

`no-framework` and `langgraph` each read the model's reasoning for CALL lines.
The parser is copied into both on purpose, since the stacks share no code, so
every case here runs against both copies and they must agree.

Neither stack is importable in this interpreter: `ollama`, `langchain_ollama`
and `langgraph.graph` live in the stacks' own environments and are absent from
this one. Module level in both files is imports, constants and defs, so a stub
with no behaviour is enough to load the file and call the real function.
"""

import importlib.util
import sys
import types

import pytest

from carbonara import registry

#: What each stack needs present before its file will import. The names are
#: stubbed, never installed, because installing them here is the thing the
#: interpreter split exists to prevent.
STUBBED = {
    "no-framework": ("ollama",),
    "langgraph": ("langchain_ollama", "langgraph", "langgraph.graph"),
}

DOERS = ("boil_pasta", "fry_guanciale", "make_egg_sauce", "grate_cheese", "combine")


class Anything:
    """Stand in for whatever a stubbed module is asked for.

    `langgraph` builds its LLM client at module level, so the stub has to
    survive being called and having attributes read off the result.
    """

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return Anything()

    def __getattr__(self, attribute):
        return Anything()


def load(name, monkeypatch):
    """Import a stack's carbonara.py with its third-party imports stubbed."""
    for module_name in STUBBED[name]:
        stub = types.ModuleType(module_name)
        stub.__getattr__ = lambda attribute: Anything()
        monkeypatch.setitem(sys.modules, module_name, stub)

    path = registry.find(name).script
    spec = importlib.util.spec_from_file_location(f"stack_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=("no-framework", "langgraph"))
def parse(request, monkeypatch):
    """Yield each stack's parse_plan in turn."""
    return load(request.param, monkeypatch).parse_plan


# The three shapes below are real captures, not invented. The bare one comes
# from qwen2.5-coder:3b, the decorated two from tiny-aya on the same prompt.

BARE = """To make a carbonara:
CALL boil_pasta: Boil pasta to the right doneness.
CALL fry_guanciale: Render guanciale until crisp.
CALL make_egg_sauce: Whisk eggs into a sauce base.
CALL grate_cheese: Grate Pecorino Romano cheese.
CALL combine: Combine all components into the final dish.
"""

NUMBERED_AND_BOLD = """**Step-by-Step Carbonara Preparation:**

1. **CALL boil_pasta:** Boil 250g of spaghetti until al dente.
2. **CALL fry_guanciale:** Fry 100g of guanciale until crispy, then set aside.
3. **CALL make_egg_sauce:** Whisk 4 eggs with 50g of Pecorino Romano.
4. **CALL grate_cheese:** Grate an additional 50g of Pecorino Romano cheese.
5. **CALL combine:** Toss the spaghetti with the egg sauce.
"""

BOLD_NAME = """**Step-by-Step Carbonara Recipe**

CALL **boil_pasta**: Boil 200g of spaghetti until al dente.
CALL **fry_guanciale**: Fry 100g of guanciale in a pan until crispy.
CALL **make_egg_sauce**: Whisk 2 eggs with grated Pecorino Romano.
CALL **grate_cheese**: Grate Pecorino Romano cheese.
CALL **combine**: Add the cooked pasta to the egg sauce.
"""


@pytest.mark.parametrize("reasoning", (BARE, NUMBERED_AND_BOLD, BOLD_NAME))
def test_a_whole_plan_survives_however_it_is_dressed(parse, reasoning):
    """Bare, numbered-and-bold, and bold-name all yield the same five doers."""
    assert [name for name, _ in parse(reasoning)] == list(DOERS)


def test_the_instruction_comes_back_without_its_decoration(parse):
    """The doer is handed a clean instruction, not one full of asterisks."""
    plan = dict(parse(NUMBERED_AND_BOLD))
    assert plan["boil_pasta"] == "Boil 250g of spaghetti until al dente."


def test_an_unknown_doer_is_dropped(parse):
    """A name that is not in the registry cannot enter the plan."""
    reasoning = "CALL sous_vide_the_egg: Hold at 63C.\nCALL combine: Plate it."
    assert [name for name, _ in parse(reasoning)] == ["combine"]


def test_a_repeated_doer_is_taken_once(parse):
    """The first instruction for a doer wins and the later one is dropped."""
    reasoning = (
        "CALL combine: Toss the pasta through the sauce.\n"
        "CALL combine: Serve immediately with extra pepper.\n"
    )
    assert parse(reasoning) == [("combine", "Toss the pasta through the sauce.")]


def test_a_doer_named_in_passing_is_not_a_call(parse):
    """Only a line that opens with CALL is a call, so prose cannot plan."""
    reasoning = "I will then CALL combine: but only once the pasta is drained."
    assert parse(reasoning) == []


def test_reasoning_with_no_call_lines_yields_no_plan(parse):
    """The empty plan is what the dispatcher's apology path depends on."""
    reasoning = "Carbonara needs guanciale, eggs, Pecorino and spaghetti."
    assert parse(reasoning) == []
