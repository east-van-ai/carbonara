"""
# ~~~ ~~~ ~~~ ~~~ ~~~ carbonara prep ~~~ ~~~ ~~~ ~~~ ~~~
#
# Prep a stack's station: build its virtual environment, from the
# interpreter it pins and its own pinned requirements. Running prep
# again rebuilds on top of what is there, which is how a half-finished
# install gets repaired.
#
# cook-with preps a stack on its own the first time, so prep is for
# doing it deliberately, ahead of a demo rather than during one.
#
# Usage:
#
#    carbonara prep STACK [--latest]
#
# STACK is one of: no-framework, crewai, langgraph, smolagents.
#
# Options:
#
#    --latest            install from requirements.txt instead of the
#                        pinned set. Pinned by default: a demo that
#                        behaves the way it behaved yesterday is worth
#                        more than one on the newest resolvable tree.
"""

from . import environ
from .args import EXIT_ERROR, EXIT_OK

USAGE = "carbonara prep STACK [--latest]"


def run(stack, args):
    """Build one stack's environment, reporting what it could not do."""
    interpreter = environ.check_interpreter(stack)
    if not interpreter.ok:
        environ.report(interpreter)
        return EXIT_ERROR

    print(f"\ncarbonara: prepping {stack.name}")
    if environ.build(stack, pinned=not args.latest):
        print(f"carbonara: {stack.name} is ready\n")
        return EXIT_OK

    print(f"carbonara: could not build the {stack.name} environment")
    return EXIT_ERROR
