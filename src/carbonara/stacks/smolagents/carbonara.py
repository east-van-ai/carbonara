"""
# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# contact: east-van-ai@proton.me
# ==============================================
#
# ~~~~ Agentic AI Demo (smolagents edition) ~~~~
#
# Roles:
#   Dispatcher  - takes a natural language order, knows nothing about kitchens
#   Expeditor   - a smolagents CodeAgent; reasons about the job, then writes
#                 and runs Python that calls the doers in the right order
#   Doers       - single-purpose tools; one job, one LLM call each
#
# The agentic part: the Expeditor does not pick from a registry.
# It writes Python code that calls the doers. The LLM is the coder.
#
# License: MIT
# ==============================================
"""

import os

import ollama
from smolagents import CodeAgent, LiteLLMModel, tool

# --- tweak me live at the demo ------------------------------------------------
# The values below are the demo defaults and stay editable by hand. The CLI
# overrides each through a CARBONARA_* environment variable, because it runs
# this file under a different interpreter and cannot import it.
MODEL = os.environ.get("CARBONARA_MODEL", "qwen2.5-coder:3b")
TEMPERATURE = float(os.environ.get("CARBONARA_TEMPERATURE", "0.3"))
ORDER = os.environ.get("CARBONARA_ORDER", "make me a carbonara")
# ------------------------------------------------------------------------------

CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
GREY = "\033[90m"
RESET = "\033[0m"


def label(role: str, color: str) -> str:
    return f"{color}[{role}]{RESET}"


# --- doers (smolagents @tool) -------------------------------------------------
# Each doer is a @tool. The CodeAgent can call them by name in generated code.
# One job. One LLM call.

DOER_SYSTEM = (
    "You are a line cook. You do exactly one job and report back concisely. "
    "One or two sentences. No fuss."
)


def _doer_call(name: str, instruction: str) -> str:
    print(f"  {label(f'DOER {name}', GREEN)}  {GREY}{instruction}{RESET}")
    response = ollama.chat(
        model=MODEL,
        options={"temperature": TEMPERATURE},
        messages=[
            {"role": "system", "content": DOER_SYSTEM},
            {"role": "user", "content": instruction},
        ],
    )
    result = response["message"]["content"].strip()
    print(f"  {label(f'DOER {name}', GREEN)}  {result}\n")
    return result


@tool
def boil_pasta(instruction: str) -> str:
    """Boils pasta to the right doneness.

    Args:
        instruction: What to do, e.g. 'Boil 200g spaghetti to al dente'.
    """
    return _doer_call("boil_pasta", instruction)


@tool
def fry_guanciale(instruction: str) -> str:
    """Renders guanciale until crisp.

    Args:
        instruction: What to do, e.g. 'Render guanciale until crisp and golden'.
    """
    return _doer_call("fry_guanciale", instruction)


@tool
def make_egg_sauce(instruction: str) -> str:
    """Whisks eggs and cheese into a sauce base.

    Args:
        instruction: What to do, e.g. 'Whisk 3 egg yolks with Pecorino Romano'.
    """
    return _doer_call("make_egg_sauce", instruction)


@tool
def grate_cheese(instruction: str) -> str:
    """Grates Pecorino Romano cheese.

    Args:
        instruction: What to do, e.g. 'Grate 80g Pecorino Romano finely'.
    """
    return _doer_call("grate_cheese", instruction)


@tool
def combine(instruction: str) -> str:
    """Combines all components into the final dish.

    Args:
        instruction: What to do, e.g. 'Toss pasta with guanciale fat and egg sauce off heat'.
    """
    return _doer_call("combine", instruction)


# --- expeditor (CodeAgent) ----------------------------------------------------


def build_expeditor() -> CodeAgent:
    model = LiteLLMModel(
        model_id=f"ollama_chat/{MODEL}",
        api_base="http://localhost:11434",
        api_key="local",  # required field; value ignored by Ollama
        num_ctx=8192,  # default 2048 is too small for code generation
        temperature=TEMPERATURE,
    )
    return CodeAgent(
        tools=[boil_pasta, fry_guanciale, make_egg_sauce, grate_cheese, combine],
        model=model,
        verbosity_level=1,  # prints the generated code so the audience sees it
    )


# --- dispatcher ---------------------------------------------------------------

DISPATCHER_SYSTEM = (
    "You are a restaurant dispatcher. You take orders and relay results. "
    "You know nothing about cooking. Keep it short and warm."
)


def dispatcher(order: str) -> str:
    print(f"\n{label('DISPATCHER', CYAN)} received order: \"{order}\"")
    print(f"\n{label('EXPEDITOR', YELLOW)} handing off to smolagents CodeAgent...\n")

    expeditor = build_expeditor()

    # The CodeAgent writes Python that calls the doer tools in the right order.
    # It figures out the sequence; we just give it the order and the tools.
    kitchen_result = expeditor.run(
        f"Make a carbonara. The order is: {order}. "
        "Use the available tools in a sensible order. combine() must come last. "
        "Return a one-sentence summary of what the kitchen completed."
    )

    # Dispatcher relays to guest
    response = ollama.chat(
        model=MODEL,
        options={"temperature": TEMPERATURE},
        messages=[
            {"role": "system", "content": DISPATCHER_SYSTEM},
            {
                "role": "user",
                "content": f"The kitchen says: {kitchen_result}\n\nRelay this to the guest.",
            },
        ],
    )
    return response["message"]["content"].strip()


# --- main ---------------------------------------------------------------------


def main():
    print(__doc__)
    print(f"\n{'-' * 60}")
    print(f"  Carbonara Demo (smolagents)  |  model: {MODEL}  |  temp: {TEMPERATURE}")
    print(f"{'-' * 60}")

    message = dispatcher(ORDER)
    print(f"{label('DISPATCHER', CYAN)} {message}\n")

    print(f"{'-' * 60}\n")


if __name__ == "__main__":
    main()
