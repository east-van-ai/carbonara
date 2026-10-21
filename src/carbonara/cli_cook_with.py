"""
        carbonara -- cook-with

https://github.com/east-van-ai/carbonara

Cook the carbonara with one agent stack. --venv cooks in the stack's virtual
environment, and --docker in a container. One of the two is required, and
neither is a default. A stack not yet prepped in that mode is prepped first,
so the first cook takes as long as the install and every one after it does not.

The order, the model, and the sampling knobs reach the stack as CARBONARA_*
environment variables. The stack runs under a different interpreter, so they
cannot be passed any other way. Before the stack starts, carbonara prints the
command it runs, in a form a shell can paste.

Telemetry is off for every stack unless --telemetry says otherwise.

Under --docker, the container is built from the same pinned requirements.
It sits on a locked network with no route out, and reaches Ollama on the
host through a relay. --telemetry opens the network back up.

A cook exits with the stack's own exit code.

The table below shows where each stack stands, in both modes.
"""

from . import containers, environ, errors, registry

HELP = "cook the demo with one stack"
USAGE = (
    "carbonara cook-with STACK (--venv | --docker) [--order TEXT] [--model NAME] "
    "[--temperature N] [--stream-delay N] [--telemetry]"
)
SLOTS = ("STACK",)


def overrides(args):
    """Collect the CARBONARA_* variables this invocation sets."""
    return {
        "CARBONARA_ORDER": args.order,
        "CARBONARA_MODEL": args.model,
        "CARBONARA_TEMPERATURE": args.temperature,
        "CARBONARA_STREAM_DELAY": args.stream_delay,
        "CARBONARA_OLLAMA_URL": environ.ollama_base_url(),
    }


def run(stack, args):
    """Check readiness, build the environment if needed, cook, return its code."""
    if args.docker:
        return run_docker(stack, args)

    environ.require(environ.check_ollama(args.model or registry.DEFAULT_MODEL))

    if not environ.is_built(stack):
        environ.require(environ.check_interpreter(stack))
        print(f"\ncarbonara: first cook with {stack.name}, prepping its station")
        if not environ.build(stack):
            raise errors.RuntimeFailure(f"could not build the {stack.name} environment")

    if args.telemetry:
        print("carbonara: --telemetry, leaving the framework's own defaults alone")

    return environ.run(stack, overrides(args), telemetry=args.telemetry)


def run_docker(stack, args):
    """Check readiness, build the image if needed, cook in a container."""
    environ.require(containers.check_docker())
    environ.require(environ.check_ollama(args.model or registry.DEFAULT_MODEL))

    if not containers.is_built(stack):
        print(
            f"\ncarbonara: first cook with {stack.name} in Docker, building its image"
        )
        if not containers.build(stack):
            raise errors.RuntimeFailure(
                f"could not build the {containers.image(stack)} image"
            )

    if args.telemetry:
        print("carbonara: --telemetry, leaving the framework's own defaults alone")

    return containers.run(stack, overrides(args), telemetry=args.telemetry)
