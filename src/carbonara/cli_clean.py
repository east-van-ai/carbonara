"""
# ~~~ ~~~ ~~~ ~~~ ~~~ carbonara clean ~~~ ~~~ ~~~ ~~~ ~~~
#
# Clean a stack's station: remove its virtual environment, so the next
# prep builds it from scratch rather than on top of what is there.
#
# --docker removes the stack's Docker image instead, and the locked
# network every Docker cook shares. The network outlives each cook on
# purpose, and this is the way to remove it. The next locked cook makes
# it again. The relay image stays: it is pinned by digest, so pulling it
# again would bring back the same bytes.
#
# There is no prompt, and no form that cleans every stack at once. One
# stack per call keeps a typo from reaching further than one station.
# Something already gone is reported and is not a failure, so running
# clean twice gives the same result. Docker refuses to remove an image
# or the network while a cook is using it, and clean passes that refusal
# on rather than forcing it.
#
# crewai's consent file is never touched.
#
# Usage:
#
#    carbonara clean STACK [--docker]
#
# STACK is one of: no-framework, crewai, langgraph, smolagents.
#
# Options:
#
#    --docker            remove the stack's Docker image and the locked
#                        network instead of its virtual environment.
"""

import shutil
import sys

from . import containers, environ
from .args import EXIT_ERROR, EXIT_OK

USAGE = "carbonara clean STACK [--docker]"


def run(stack, args):
    """Remove one stack's virtual environment, reporting what it could not do."""
    if args.docker:
        return run_docker(stack)

    path = environ.venv_dir(stack)
    if not path.exists() and not path.is_symlink():
        print(f"carbonara: no virtual environment for {stack.name}, nothing to clean")
        return EXIT_OK

    # carbonara only ever makes a real directory here, so anything else is not ours.
    if path.is_symlink() or not path.is_dir():
        print(
            f"carbonara: {path} is not a directory carbonara built, so it stays",
            file=sys.stderr,
        )
        return EXIT_ERROR

    try:
        shutil.rmtree(path)
    except OSError as error:
        print(f"carbonara: could not remove {path}", file=sys.stderr)
        print(f"  {error}", file=sys.stderr)
        return EXIT_ERROR

    print(f"carbonara: removed {path}")
    return EXIT_OK


def run_docker(stack):
    """Remove one stack's image and the locked network, reporting what failed.

    The network is tried even when the image fails, so both refusals show.
    """
    docker = containers.check_docker()
    if not docker.ok:
        environ.report(docker)
        return EXIT_ERROR

    tag = containers.image(stack)
    removed = True
    if containers.is_built(stack):
        removed = containers.quietly(containers.image_rm_argv(stack), f"remove {tag}")
    else:
        print(f"carbonara: no image {tag}, nothing to clean")

    if containers.network_exists():
        network = containers.quietly(
            containers.network_rm_argv(), f"remove the {containers.NETWORK} network"
        )
        removed = network and removed
    else:
        print(f"carbonara: no {containers.NETWORK} network, nothing to clean")

    return EXIT_OK if removed else EXIT_ERROR
