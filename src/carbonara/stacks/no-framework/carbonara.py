"""
# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# contact: east-van-ai@proton.me
# ==============================================
#
# ~~~~ Agentic AI Demo (no security layer) ~~~~
#
# Roles:
#   Dispatcher  - takes a natural language order, knows nothing about kitchens
#   Expeditor   - agentic brain; reasons about the job, picks doers, sequences them
#   Doers       - single-purpose workers; one job, one LLM call each
#
# The agentic part: the Expeditor is not hardcoded. The LLM figures out which
# doers to call and in what order by reasoning through the job in plain English.
#
# The Expeditor streams its reasoning token by token. On slower hardware this
# feels alive. On faster hardware, bump STREAM_DELAY to slow it down.
#
# License: MIT
# ==============================================
"""

import os
import time

import ollama

# --- tweak me live at the demo ------------------------------------------------
# The values below are the demo defaults and stay editable by hand. The CLI
# overrides each through a CARBONARA_* environment variable, because it runs
# this file under a different interpreter and cannot import it.
MODEL = os.environ.get("CARBONARA_MODEL", "qwen2.5-coder:3b")
TEMPERATURE = float(os.environ.get("CARBONARA_TEMPERATURE", "0.3"))
ORDER = os.environ.get("CARBONARA_ORDER", "make me a carbonara")
STREAM_DELAY = float(os.environ.get("CARBONARA_STREAM_DELAY", "0.0"))
# ------------------------------------------------------------------------------

CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
GREY = "\033[90m"
RESET = "\033[0m"


# --- helpers -----------------------------------------------


def llm(system: str, user: str) -> str:
    response = ollama.chat(
        model=MODEL,
        options={"temperature": TEMPERATURE},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response["message"]["content"].strip()


def llm_stream(system: str, user: str) -> str:
    """Stream tokens to stdout as they arrive. Returns the full text."""
    stream = ollama.chat(
        model=MODEL,
        options={"temperature": TEMPERATURE},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        stream=True,
    )
    full_text = ""
    for chunk in stream:
        token = chunk["message"]["content"]
        print(f"{GREY}{token}{RESET}", end="", flush=True)
        if STREAM_DELAY:
            time.sleep(STREAM_DELAY)
        full_text += token
    print()
    return full_text.strip()


def label(role: str, color: str) -> str:
    return f"{color}[{role}]{RESET}"


# --- doers --------------------------------------------------------------------
# Each doer is a line cooks. Each gets a plain English instruction and returns a plain English result.
# One job. One LLM call.

DOER_SYSTEM = (
    "You are a line cook. You do exactly one job and report back concisely. "
    "One or two sentences. No fuss."
)


def doer_boil_pasta(instruction: str) -> str:
    print(f"  {label('DOER boil_pasta', GREEN)}  {GREY}{instruction}{RESET}")
    result = llm(DOER_SYSTEM, instruction)
    print(f"  {label('DOER boil_pasta', GREEN)}  {result}\n")
    return result


def doer_fry_guanciale(instruction: str) -> str:
    print(f"  {label('DOER fry_guanciale', GREEN)}  {GREY}{instruction}{RESET}")
    result = llm(DOER_SYSTEM, instruction)
    print(f"  {label('DOER fry_guanciale', GREEN)}  {result}\n")
    return result


def doer_make_egg_sauce(instruction: str) -> str:
    print(f"  {label('DOER make_egg_sauce', GREEN)}  {GREY}{instruction}{RESET}")
    result = llm(DOER_SYSTEM, instruction)
    print(f"  {label('DOER make_egg_sauce', GREEN)}  {result}\n")
    return result


def doer_grate_cheese(instruction: str) -> str:
    print(f"  {label('DOER grate_cheese', GREEN)}  {GREY}{instruction}{RESET}")
    result = llm(DOER_SYSTEM, instruction)
    print(f"  {label('DOER grate_cheese', GREEN)}  {result}\n")
    return result


def doer_combine(instruction: str) -> str:
    print(f"  {label('DOER combine', GREEN)}  {GREY}{instruction}{RESET}")
    result = llm(DOER_SYSTEM, instruction)
    print(f"  {label('DOER combine', GREEN)}  {result}\n")
    return result


# Registry: name -> (callable, one-line capability description)
# The Expeditor sees the names and descriptions. She picks doers from this list.

DOER_REGISTRY = {
    "boil_pasta": (doer_boil_pasta, "boils pasta to the right doneness"),
    "fry_guanciale": (doer_fry_guanciale, "renders guanciale until crisp"),
    "make_egg_sauce": (doer_make_egg_sauce, "whisks eggs into a sauce base"),
    "grate_cheese": (doer_grate_cheese, "grates Pecorino Romano cheese"),
    "combine": (doer_combine, "combines all components into the final dish"),
}


# --- expeditor ----------------------------------------------------------------

EXPEDITOR_SYSTEM = """You are a kitchen expeditor. You coordinate line cooks to complete a dish.

You have these doers available:
{registry}

When given an order, reason through what needs to happen step by step.
Think out loud. Then list the doers you will call, in order, one per line, like this:

CALL boil_pasta: <instruction for that doer>
CALL fry_guanciale: <instruction for that doer>
... and so on.

Only use doers from the list above. Sequence matters - combine always comes last."""


def expeditor(order: str) -> list[tuple]:
    registry_text = "\n".join(
        f"  {name}: {desc}" for name, (_, desc) in DOER_REGISTRY.items()
    )
    system = EXPEDITOR_SYSTEM.format(registry=registry_text)

    print(f"\n{label('EXPEDITOR', YELLOW)} thinking about: \"{order}\"\n")

    # Stream the reasoning so the audience watches it think in real time.
    # On fast hardware, set STREAM_DELAY > 0 to restore the drama.
    reasoning = llm_stream(system, order)
    print()

    # Parse CALL lines into (doer_name, instruction) pairs.
    # e.g. "CALL boil_pasta: Boil 200g spaghetti to al dente"
    # to ("boil_pasta", "Boil 200g spaghetti to al dente")
    plan = []
    for line in reasoning.splitlines():
        line_stripped = line.strip().upper()
        if not line_stripped.startswith(("CALL ", "- CALL ")):
            continue
        prefix = "- CALL " if line_stripped.startswith("- CALL ") else "CALL "
        rest = line.strip()[len(prefix) :]
        if ":" not in rest:
            continue
        name, instruction = rest.split(":", 1)
        name = name.strip()
        if name not in DOER_REGISTRY:
            continue
        if any(item[0] == name for item in plan):
            continue
        plan.append((name, instruction.strip()))

    return plan


# --- dispatcher ---------------------------------------------------------------

DISPATCHER_SYSTEM = (
    "You are a restaurant dispatcher. You take orders and relay results. "
    "You know nothing about cooking. Keep it short and warm."
)


def dispatcher(order: str) -> str:
    print(f"\n{label('DISPATCHER', CYAN)} received order: \"{order}\"")

    # hand off to expeditor
    plan = expeditor(order)

    if not plan:
        return "Sorry, the kitchen couldn't figure out what to do with that."

    # execute the plan
    print(
        f"{label('EXPEDITOR', YELLOW)} executing plan: {[name for name, _ in plan]}\n"
    )
    results = []
    for name, instruction in plan:
        fn, _ = DOER_REGISTRY[name]
        result = fn(instruction)
        results.append(f"{name}: {result}")

    # expeditor summarises for the dispatcher
    summary_prompt = (
        "The kitchen completed these steps:\n"
        + "\n".join(results)
        + "\n\nGive the dispatcher a one-sentence status to pass to the guest."
    )
    kitchen_summary = llm(
        "You are a kitchen expeditor. Summarise the completed dish for the front of house.",
        summary_prompt,
    )

    # dispatcher delivers to guest
    guest_message = llm(
        DISPATCHER_SYSTEM,
        f"The kitchen says: {kitchen_summary}\n\nRelay this to the guest.",
    )

    return guest_message


# --- main ---------------------------------------------------------------------


def main():
    print(__doc__)
    print(f"\n{'-' * 60}")
    print(f"  Carbonara Demo  |  model: {MODEL}  |  temp: {TEMPERATURE}")
    print(f"{'-' * 60}")

    message = dispatcher(ORDER)
    print(f"{label('DISPATCHER', CYAN)} {message}\n")

    print(f"{'-' * 60}\n")


if __name__ == "__main__":
    main()
