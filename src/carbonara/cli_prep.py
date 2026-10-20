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
# --docker builds the stack's Docker image instead, from the same
# requirements file. The two are independent: a stack can have either,
# both, or neither.
#
# Usage:
#
#    carbonara prep STACK [--latest] [--docker]
#
# STACK is one of: no-framework, crewai, langgraph, smolagents.
#
# Options:
#
#    --latest            install from requirements.txt instead of the
#                        pinned set. Pinned by default: a demo that
#                        behaves the way it behaved yesterday is worth
#                        more than one on the newest resolvable tree.
#    --docker            build the stack's Docker image instead of its
#                        virtual environment.
"""

from . import containers, environ
from .args import EXIT_ERROR, EXIT_OK

USAGE = "carbonara prep STACK [--latest] [--docker]"


def run(stack, args):
    """Build one stack's environment, reporting what it could not do."""
    if args.docker:
        return run_docker(stack, args)

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


def run_docker(stack, args):
    """Build one stack's Docker image, reporting what it could not do."""
    docker = containers.check_docker()
    if not docker.ok:
        environ.report(docker)
        return EXIT_ERROR

    print(f"\ncarbonara: prepping {stack.name} in Docker")
    if containers.build(stack, pinned=not args.latest):
        print(f"carbonara: {containers.image(stack)} is ready\n")
        return EXIT_OK

    print(f"carbonara: could not build the {containers.image(stack)} image")
    return EXIT_ERROR
