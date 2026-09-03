"""
# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# contact: east-van-ai@proton.me
# ==============================================
#
# ~~~~ Agentic AI Demo (CrewAI edition) ~~~~
#
# Roles:
#   Dispatcher  - takes a natural language order, knows nothing about kitchens
#   Expeditor   - a CrewAI Agent; reasons about the job, sequences the doers
#   Doers       - CrewAI Agents with a single role each; one job, one LLM call
#
# The CrewAI way: agents have a role, a goal, and a backstory.
# Tasks wire agents together. A Crew runs the whole thing sequentially.
# The Expeditor plans; the doers execute in order.
#
# License: MIT
# ==============================================
"""

import os
import warnings

warnings.filterwarnings("ignore")

from crewai import LLM, Agent, Crew, Task

# --- tweak me live at the demo ------------------------------------------------
# The values below are the demo defaults and stay editable by hand. The CLI
# overrides each through a CARBONARA_* environment variable, because it runs
# this file under a different interpreter and cannot import it.
MODEL = os.environ.get("CARBONARA_MODEL", "hf.co/CohereLabs/tiny-aya-global-GGUF:Q4_K_M")
TEMPERATURE = float(os.environ.get("CARBONARA_TEMPERATURE", "0.3"))
ORDER = os.environ.get("CARBONARA_ORDER", "make me a carbonara")
# ------------------------------------------------------------------------------

CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"


def label(role: str, color: str) -> str:
    return f"{color}[{role}]{RESET}"


# --- local LLM ----------------------------------------------------------------

llm = LLM(
    model=f"ollama/{MODEL}",
    base_url="http://localhost:11434",
    temperature=TEMPERATURE,
)


# --- agents -------------------------------------------------------------------
# CrewAI agents have three things: role, goal, backstory.
# Role is their job title. Goal is what they are trying to achieve.
# Backstory is the context that shapes how they reason.

dispatcher_agent = Agent(
    role="Restaurant Dispatcher",
    goal="Receive guest orders and relay kitchen results back warmly and concisely.",
    backstory=(
        "You work front of house. You take orders in plain English and pass "
        "results to guests. You know nothing about cooking and don't need to."
    ),
    llm=llm,
    verbose=False,
)

expeditor_agent = Agent(
    role="Kitchen Expeditor",
    goal="Plan and sequence the kitchen steps needed to complete a dish.",
    backstory=(
        "You coordinate the kitchen. Given an order, you reason through what "
        "needs to happen and in what order. You assign clear, specific "
        "instructions to each station."
    ),
    llm=llm,
    verbose=True,
)

pasta_agent = Agent(
    role="Pasta Cook",
    goal="Boil pasta to the correct doneness and report back.",
    backstory="You run the pasta station. One job: perfect pasta every time.",
    llm=llm,
    verbose=False,
)

guanciale_agent = Agent(
    role="Meat Cook",
    goal="Render guanciale until crisp and report back.",
    backstory="You run the meat station. One job: crisp guanciale, fat in the pan.",
    llm=llm,
    verbose=False,
)

sauce_agent = Agent(
    role="Sauce Cook",
    goal="Whisk eggs and cheese into a smooth sauce base and report back.",
    backstory="You run the sauce station. One job: silky egg sauce, no scrambling.",
    llm=llm,
    verbose=False,
)

cheese_agent = Agent(
    role="Prep Cook",
    goal="Grate Pecorino Romano finely and report back.",
    backstory="You handle prep. One job: freshly grated cheese, ready to go.",
    llm=llm,
    verbose=False,
)

combine_agent = Agent(
    role="Finishing Cook",
    goal="Combine all components into the final dish and report back.",
    backstory=(
        "You do the final plate. One job: bring everything together off the heat, "
        "silky and perfect."
    ),
    llm=llm,
    verbose=False,
)


# --- tasks --------------------------------------------------------------------
# Tasks wire agents to work. context= declares dependencies -- a task waits
# for its context tasks to finish before it runs.

receive_task = Task(
    description=f"Receive this order from the guest: '{ORDER}'. Confirm it.",
    expected_output="A one-sentence confirmation that the order was received.",
    agent=dispatcher_agent,
)

plan_task = Task(
    description=(
        f"The guest ordered: {ORDER}. Plan the kitchen steps. "
        "Write a specific instruction for each station: pasta, meat, sauce, prep, finishing. "
        "Be concise and direct."
    ),
    expected_output="A numbered list of station instructions for making carbonara.",
    agent=expeditor_agent,
    context=[receive_task],
)

pasta_task = Task(
    description="Follow the pasta instruction from the expeditor's plan. Report what you did in one sentence.",
    expected_output="One sentence: what the pasta station completed.",
    agent=pasta_agent,
    context=[plan_task],
)

guanciale_task = Task(
    description="Follow the meat instruction from the expeditor's plan. Report what you did in one sentence.",
    expected_output="One sentence: what the meat station completed.",
    agent=guanciale_agent,
    context=[plan_task],
)

sauce_task = Task(
    description="Follow the sauce instruction from the expeditor's plan. Report what you did in one sentence.",
    expected_output="One sentence: what the sauce station completed.",
    agent=sauce_agent,
    context=[plan_task],
)

cheese_task = Task(
    description="Follow the prep instruction from the expeditor's plan. Report what you did in one sentence.",
    expected_output="One sentence: what the prep station completed.",
    agent=cheese_agent,
    context=[plan_task],
)

combine_task = Task(
    description=(
        "Follow the finishing instruction from the expeditor's plan. "
        "All other stations are done. Combine everything. "
        "Report what you did in one sentence."
    ),
    expected_output="One sentence: what the finishing station completed.",
    agent=combine_agent,
    context=[pasta_task, guanciale_task, sauce_task, cheese_task],
)

deliver_task = Task(
    description=(
        "The kitchen is done. Relay the result to the guest warmly and briefly. "
        "You know nothing about cooking -- just pass on that their carbonara is ready."
    ),
    expected_output="A warm one-sentence message to the guest.",
    agent=dispatcher_agent,
    context=[combine_task],
)


# --- crew ---------------------------------------------------------------------


def build_crew() -> Crew:
    return Crew(
        agents=[
            dispatcher_agent,
            expeditor_agent,
            pasta_agent,
            guanciale_agent,
            sauce_agent,
            cheese_agent,
            combine_agent,
        ],
        tasks=[
            receive_task,
            plan_task,
            pasta_task,
            guanciale_task,
            sauce_task,
            cheese_task,
            combine_task,
            deliver_task,
        ],
        verbose=False,
    )


# --- main ---------------------------------------------------------------------


def main():
    print(__doc__)
    print(f"\n{'-' * 60}")
    print(f"  Carbonara Demo (CrewAI)  |  model: {MODEL}  |  temp: {TEMPERATURE}")
    print(f"{'-' * 60}\n")

    print(f"{label('DISPATCHER', CYAN)} received order: \"{ORDER}\"\n")
    print(f"{label('EXPEDITOR', YELLOW)} handing off to CrewAI...\n")

    crew = build_crew()
    result = crew.kickoff()

    print(f"\n{label('DISPATCHER', CYAN)} {result}\n")
    print(f"{'-' * 60}\n")


if __name__ == "__main__":
    main()
