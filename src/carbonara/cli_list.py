"""
# ~~~ ~~~ ~~~ ~~~ ~~~ carbonara list ~~~ ~~~ ~~~ ~~~ ~~~
#
# Print the four agent stacks, the interpreter each one wants, whether
# its environment and its Docker image are built, and which of them
# reaches the network on its own account. Ollama's and Docker's state
# go underneath, along with where the environments live. This is the
# command that answers "why did that fail", and the one that answers
# "which of these is watching me".
#
# Usage:
#
#    carbonara list
#
# list takes no STACK and no options. Its bare form is already a
# complete command line, so it runs rather than documenting itself.
"""

from . import containers, environ, registry

USAGE = "carbonara list"


def state(stack):
    """Describe one stack's environment in a few words."""
    if environ.is_built(stack):
        return "ready"
    interpreter = environ.check_interpreter(stack)
    if not interpreter.ok:
        return f"no python {stack.python_version}"
    return "not built"


def image_state(stack, docker):
    """Describe one stack's Docker image in a few words."""
    if not docker.ok:
        return "no docker"
    return "built" if containers.is_built(stack) else "not built"


def run(args):
    """Print every stack's state, then Ollama's and Docker's."""
    docker = containers.check_docker()
    rows = [
        (
            s.name,
            s.python_version,
            state(s),
            image_state(s, docker),
            "yes" if s.phones_home else "no",
            s.summary,
        )
        for s in registry.stacks()
    ]
    # Each column is as wide as its widest cell or its own heading, whichever
    # is more. "ENVIRONMENT" is longer than anything that ever sits under it.
    width = max(len("STACK"), *(len(row[0]) for row in rows))
    state_width = max(len("ENVIRONMENT"), *(len(row[2]) for row in rows))
    image_width = max(len("IMAGE"), *(len(row[3]) for row in rows))

    print()
    print(
        f"  {'STACK':<{width}}  PYTHON  {'ENVIRONMENT':<{state_width}}  "
        f"{'IMAGE':<{image_width}}  CALLS HOME"
    )
    for name, version, condition, built, calls, summary in rows:
        print(
            f"  {name:<{width}}  {version:<6}  {condition:<{state_width}}  "
            f"{built:<{image_width}}  {calls:<10}  {summary}"
        )

    ollama = environ.check_ollama()
    print()
    if ollama.ok:
        print(f"  ollama at {environ.ollama_base_url()} has {registry.DEFAULT_MODEL}")
    else:
        print(f"  {ollama.problem}")
        print(f"  try: {ollama.fix}")
    if docker.ok:
        print("  docker is running, for --docker")
    else:
        print(f"  {docker.problem}")
        print(f"  try: {docker.fix}")
    print()
    print(f"  environments live in {environ.venvs_root()}")
    print(
        f"  {len(registry.PHONES_HOME)} of the {len(registry.NAMES)} stacks reach "
        "the network on their own account."
    )
    print("  carbonara silences all of them; --telemetry on a cook hands it back")
    print()
    return 0
