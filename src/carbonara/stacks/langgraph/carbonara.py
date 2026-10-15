"""
# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# contact: east-van-ai@proton.me
# ==============================================
#
# ~~~~ Agentic AI Demo (LangGraph edition) ~~~~
#
# Roles (same as original):
#   Dispatcher  -- takes a natural language order, knows nothing about kitchens
#   Expeditor   -- agentic brain; reasons about the job, picks doers, sequences them
#   Doers       -- single-purpose workers; one job, one LLM call each
#
# What changes with LangGraph:
#   - State is a typed dict flowing through a graph of nodes
#   - Edges declare what runs next (statically OR conditionally)
#   - The graph is compiled, visualisable, and replayable
#   - No manual "for name, instruction in plan" loop -- the graph drives it
#
# License: MIT
# ==============================================
"""

import operator
import os
import re
from typing import Annotated, TypedDict

from langchain_ollama import OllamaLLM
from langgraph.graph import END, StateGraph

# --- tweak me live at the demo ------------------------------------------------
# The values below are the demo defaults and stay editable by hand. The CLI
# overrides each through a CARBONARA_* environment variable, because it runs
# this file under a different interpreter and cannot import it.
MODEL = os.environ.get("CARBONARA_MODEL", "hf.co/CohereLabs/tiny-aya-global-GGUF:Q4_K_M")
TEMPERATURE = float(os.environ.get("CARBONARA_TEMPERATURE", "0.3"))
ORDER = os.environ.get("CARBONARA_ORDER", "make me a carbonara")
OLLAMA_URL = os.environ.get("CARBONARA_OLLAMA_URL", "http://localhost:11434")
# ------------------------------------------------------------------------------

CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
GREY = "\033[90m"
RESET = "\033[0m"

llm = OllamaLLM(model=MODEL, temperature=TEMPERATURE, base_url=OLLAMA_URL)


def label(role: str, color: str) -> str:
    return f"{color}[{role}]{RESET}"


# --- graph state --------------------------------------------------------------
# This is the key LangGraph concept: all data lives here and flows between nodes.
# `operator.add` on the results list means each node appends; it never overwrites.


class KitchenState(TypedDict):
    order: str  # the original guest order
    plan: list[tuple[str, str]]  # [(doer_name, instruction), ...]
    plan_index: int  # which doer we are up to
    results: Annotated[list[str], operator.add]  # accumulates doer outputs
    kitchen_summary: str  # expeditor summary for dispatcher
    guest_message: str  # final message to the guest


# --- doer registry ------------------------------------------------------------

DOER_SYSTEM = (
    "You are a line cook. You do exactly one job and report back concisely. "
    "One or two sentences. No fuss."
)

DOER_REGISTRY = {
    "boil_pasta": "boils pasta to the right doneness",
    "fry_guanciale": "renders guanciale until crisp",
    "make_egg_sauce": "whisks eggs into a sauce base",
    "grate_cheese": "grates Pecorino Romano cheese",
    "combine": "combines all components into the final dish",
}


# --- nodes --------------------------------------------------------------------

#: A CALL line, once the decoration is off it. Anchored, so a doer named in
#: passing mid-sentence is not a call.
CALL_LINE = re.compile(r"CALL\s+([a-z_]+)\s*:\s*(.+)", re.IGNORECASE)

#: Leading bullets and list numbers, which models add without being asked.
LIST_PREFIX = re.compile(r"^[\s>]*(?:[-*+]\s*|\d+[.)]\s*)*")


def parse_plan(reasoning: str) -> list[tuple]:
    """Read the expeditor's CALL lines into (doer_name, instruction) pairs.

    e.g. "CALL boil_pasta: Boil 200g spaghetti to al dente"
    to ("boil_pasta", "Boil 200g spaghetti to al dente").

    Models decorate. The same line arrives as "1. **CALL boil_pasta:** ..."
    or "CALL **boil_pasta**: ..." depending on who is answering, so list
    markers and asterisks come off before the match. The registry lookup and
    the de-duplication below are what keep the plan honest, which is why
    widening the match cannot invent a step.
    """
    plan = []
    seen = set()
    for line in reasoning.splitlines():
        clean = LIST_PREFIX.sub("", line.strip()).replace("*", "")
        match = CALL_LINE.match(clean)
        if not match:
            continue
        name = match.group(1)
        if name not in DOER_REGISTRY or name in seen:
            continue
        seen.add(name)
        plan.append((name, match.group(2).strip()))

    return plan


def node_dispatcher_receive(state: KitchenState) -> dict:
    """Dispatcher receives the order. No cooking knowledge needed."""
    print(f"\n{label('DISPATCHER', CYAN)} received order: \"{state['order']}\"")
    return {}  # nothing to add to state yet; just a log step


EXPEDITOR_SYSTEM = """You are a kitchen expeditor. You coordinate line cooks to complete a dish.

You have these doers available:
{registry}

When given an order, reason through what needs to happen step by step.
Think out loud. Then list the doers you will call, in order, one per line, like this:

CALL boil_pasta: <instruction for that doer>
CALL fry_guanciale: <instruction for that doer>
... and so on.

Only use doers from the list above. Sequence matters -- combine always comes last."""


def node_expeditor_plan(state: KitchenState) -> dict:
    """Expeditor reasons through the job and builds a plan."""
    registry_text = "\n".join(
        f"  {name}: {desc}" for name, desc in DOER_REGISTRY.items()
    )
    system = EXPEDITOR_SYSTEM.format(registry=registry_text)

    print(f"\n{label('EXPEDITOR', YELLOW)} thinking about: \"{state['order']}\"\n")
    reasoning = llm.invoke(f"{system}\n\nOrder: {state['order']}").strip()

    for line in reasoning.splitlines():
        print(f"  {GREY}{line}{RESET}")
    print()

    return {"plan": parse_plan(reasoning), "plan_index": 0}


def node_run_doer(state: KitchenState) -> dict:
    """Run the next doer in the plan."""
    idx = state["plan_index"]
    name, instruction = state["plan"][idx]

    print(f"  {label(f'DOER {name}', GREEN)}  {GREY}{instruction}{RESET}")
    result = llm.invoke(f"{DOER_SYSTEM}\n\nJob: {instruction}").strip()
    print(f"  {label(f'DOER {name}', GREEN)}  {result}\n")

    return {
        "results": [f"{name}: {result}"],
        "plan_index": idx + 1,
    }


def node_expeditor_summarise(state: KitchenState) -> dict:
    """Expeditor wraps up all doer results into one summary."""
    summary_prompt = (
        "The kitchen completed these steps:\n"
        + "\n".join(state["results"])
        + "\n\nGive the dispatcher a one-sentence status to pass to the guest."
    )
    system = "You are a kitchen expeditor. Summarise the completed dish for the front of house."
    summary = llm.invoke(f"{system}\n\n{summary_prompt}").strip()
    return {"kitchen_summary": summary}


def node_dispatcher_deliver(state: KitchenState) -> dict:
    """Dispatcher relays the kitchen summary to the guest."""
    system = (
        "You are a restaurant dispatcher. You take orders and relay results. "
        "You know nothing about cooking. Keep it short and warm."
    )
    guest_message = llm.invoke(
        f"{system}\n\nThe kitchen says: {state['kitchen_summary']}\n\nRelay this to the guest."
    ).strip()
    return {"guest_message": guest_message}


# --- routing ------------------------------------------------------------------


def should_continue_doers(state: KitchenState) -> str:
    """Conditional edge: keep running doers, or move on to summary."""
    if state["plan_index"] < len(state["plan"]):
        return "run_doer"
    return "summarise"


# --- build the graph ----------------------------------------------------------


def build_graph() -> StateGraph:
    graph = StateGraph(KitchenState)

    graph.add_node("dispatcher_receive", node_dispatcher_receive)
    graph.add_node("expeditor_plan", node_expeditor_plan)
    graph.add_node("run_doer", node_run_doer)
    graph.add_node("expeditor_summarise", node_expeditor_summarise)
    graph.add_node("dispatcher_deliver", node_dispatcher_deliver)

    graph.set_entry_point("dispatcher_receive")

    graph.add_edge("dispatcher_receive", "expeditor_plan")
    graph.add_edge("expeditor_plan", "run_doer")

    # Loop: run_doer → run_doer (more doers left) OR run_doer → summarise (done)
    graph.add_conditional_edges(
        "run_doer",
        should_continue_doers,
        {
            "run_doer": "run_doer",
            "summarise": "expeditor_summarise",
        },
    )

    graph.add_edge("expeditor_summarise", "dispatcher_deliver")
    graph.add_edge("dispatcher_deliver", END)

    return graph.compile()


# --- main ---------------------------------------------------------------------


def main():
    print(__doc__)
    print(f"\n{'-' * 60}")
    print(f"  Carbonara Demo (LangGraph)  |  model: {MODEL}  |  temp: {TEMPERATURE}")
    print(f"{'-' * 60}")

    app = build_graph()

    initial_state: KitchenState = {
        "order": ORDER,
        "plan": [],
        "plan_index": 0,
        "results": [],
        "kitchen_summary": "",
        "guest_message": "",
    }

    final_state = app.invoke(initial_state)

    print(f"{label('DISPATCHER', CYAN)} {final_state['guest_message']}\n")
    print(f"{'-' * 60}\n")


if __name__ == "__main__":
    main()
