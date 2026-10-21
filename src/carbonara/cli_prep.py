"""
        carbonara -- prep

https://github.com/east-van-ai/carbonara

Prep a stack's station from its own pinned requirements. --venv builds a
virtual environment from the interpreter the stack pins. --docker builds a
Docker image. One of the two is required, and neither is a default. The two
are independent: a stack can have either, both, or neither.

Running prep again rebuilds on top of what is there, which is how a
half-finished install gets repaired. cook-with preps a stack on its own the
first time, so prep is for doing it deliberately, ahead of a demo rather than
during one.

The table below shows where each stack stands, in both modes.
"""

from . import containers, environ, errors

HELP = "prep a stack's station"
USAGE = "carbonara prep STACK (--venv | --docker) [--latest]"
SLOTS = ("STACK",)


def run(stack, args):
    """Build one stack's environment, or raise what stopped it."""
    if args.docker:
        run_docker(stack, args)
        return

    environ.require(environ.check_interpreter(stack))

    print(f"\ncarbonara: prepping {stack.name}")
    if not environ.build(stack, pinned=not args.latest):
        raise errors.RuntimeFailure(f"could not build the {stack.name} environment")
    print(f"carbonara: {stack.name} is ready\n")


def run_docker(stack, args):
    """Build one stack's Docker image, or raise what stopped it."""
    environ.require(containers.check_docker())

    print(f"\ncarbonara: prepping {stack.name} in Docker")
    if not containers.build(stack, pinned=not args.latest):
        raise errors.RuntimeFailure(
            f"could not build the {containers.image(stack)} image"
        )
    print(f"carbonara: {containers.image(stack)} is ready\n")
