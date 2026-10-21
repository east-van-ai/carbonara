"""
        carbonara -- clean

https://github.com/east-van-ai/carbonara

Clean a stack's station, so the next prep builds it from scratch rather than
on top of what is there. --venv removes the stack's virtual environment.
One of the two is required, and neither is a default.

--docker removes the stack's Docker image, and the locked network every
Docker cook shares. The network outlives each cook, and this is the way to
remove it. The next locked cook makes it again. A relay left by a cook that
was killed goes first, since it holds the network; one serving a running cook
stays. The relay image stays.

There is no prompt, and no form that cleans every stack at once. Something
already gone is reported and is not a failure, so running clean twice gives
the same result. Docker refuses to remove an image or the network while a
cook is using it, and clean passes that refusal on rather than forcing it.

crewai's consent file is never touched.

The table below shows where each stack stands, in both modes.
"""

import shutil

from . import containers, environ, errors

HELP = "clean a stack's station"
USAGE = "carbonara clean STACK (--venv | --docker)"
SLOTS = ("STACK",)


def run(stack, args):
    """Remove one stack's virtual environment, or raise what stopped it."""
    if args.docker:
        run_docker(stack)
        return

    path = environ.venv_dir(stack)
    if not path.exists() and not path.is_symlink():
        print(f"carbonara: no virtual environment for {stack.name}, nothing to clean")
        return

    # carbonara only ever makes a real directory here, so anything else is not ours.
    if path.is_symlink() or not path.is_dir():
        raise errors.ReadinessError(
            f"{path} is not a directory carbonara built, so it stays"
        )

    try:
        shutil.rmtree(path)
    except OSError as error:
        raise errors.RuntimeFailure(f"could not remove {path}\n  {error}") from None

    print(f"carbonara: removed {path}")


def run_docker(stack):
    """Remove one stack's image and the locked network, or raise what failed.

    The network is tried even when the image fails, so both refusals show.
    """
    environ.require(containers.check_docker())

    tag = containers.image(stack)
    refusals = []
    if containers.is_built(stack):
        refusals.append(
            containers.quietly(containers.image_rm_argv(stack), f"remove {tag}")
        )
    else:
        print(f"carbonara: no image {tag}, nothing to clean")

    # A relay left by a killed cook holds the network, so it goes first.
    for relay in containers.orphaned_relays():
        refusals.append(
            containers.quietly(
                containers.relay_rm_argv(relay), f"remove the orphaned relay {relay}"
            )
        )

    if containers.network_exists():
        refusals.append(
            containers.quietly(
                containers.network_rm_argv(),
                f"remove the {containers.NETWORK} network",
            )
        )
    else:
        print(f"carbonara: no {containers.NETWORK} network, nothing to clean")

    refused = [refusal for refusal in refusals if refusal]
    if refused:
        raise errors.RuntimeFailure("\ncarbonara: ".join(refused))
