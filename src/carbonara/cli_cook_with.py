"""
# ~~~ ~~~ ~~~ ~~~ ~~~ carbonara cook-with ~~~ ~~~ ~~~ ~~~ ~~~
#
# Cook the carbonara with one agent stack, in a virtual environment of
# its own. A stack with no environment yet is prepped first, so the first
# cook with a stack takes as long as the install and every one after it
# does not.
#
# The order, the model, and the sampling knobs reach the stack as
# CARBONARA_* environment variables. The stack runs under a different
# interpreter, so they cannot be passed any other way.
#
# Telemetry is off for every stack unless --telemetry says otherwise.
#
# --docker cooks in a container instead, built from the same pinned
# requirements. The container sits on a locked network with no route
# out, and reaches Ollama on the host through a relay. --telemetry opens
# the network back up.
#
# Usage:
#
#    carbonara cook-with STACK [--order TEXT] [--model NAME]
#    carbonara cook-with STACK [--temperature N] [--stream-delay N]
#    carbonara cook-with STACK [--telemetry] [--docker]
#
# STACK is one of: no-framework, crewai, langgraph, smolagents.
#
# Options:
#
#    --order TEXT        the order to give the kitchen. Default is
#                        "make me a carbonara".
#    --model NAME        Ollama model. Default is
#                        hf.co/CohereLabs/tiny-aya-global-GGUF:Q4_K_M.
#    --temperature N     0.0 to 2.0. Near zero keeps the plan stable.
#                        Push it up and the expeditor improvises.
#    --stream-delay N    seconds per token, for slowing the reasoning
#                        trace down on fast hardware.
#    --telemetry         leave the framework's own telemetry defaults
#                        alone. Off by default.
#    --docker            cook in a Docker container, behind a locked network.
#                        Builds the stack's image first if it has none.
"""

from . import containers, environ, registry
from .args import EXIT_ERROR

USAGE = "carbonara cook-with STACK [--order TEXT] [--model NAME] [--temperature N]"


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
    """Check readiness, build the environment if needed, then cook."""
    if args.docker:
        return run_docker(stack, args)

    ollama = environ.check_ollama(args.model or registry.DEFAULT_MODEL)
    if not ollama.ok:
        environ.report(ollama)
        return EXIT_ERROR

    if not environ.is_built(stack):
        interpreter = environ.check_interpreter(stack)
        if not interpreter.ok:
            environ.report(interpreter)
            return EXIT_ERROR
        print(f"\ncarbonara: first cook with {stack.name}, prepping its station")
        if not environ.build(stack):
            print(f"carbonara: could not build the {stack.name} environment")
            return EXIT_ERROR

    if args.telemetry:
        print("carbonara: --telemetry, leaving the framework's own defaults alone")

    return environ.run(stack, overrides(args), telemetry=args.telemetry)


def run_docker(stack, args):
    """Check readiness, build the image if needed, then cook in a container."""
    docker = containers.check_docker()
    if not docker.ok:
        environ.report(docker)
        return EXIT_ERROR

    ollama = environ.check_ollama(args.model or registry.DEFAULT_MODEL)
    if not ollama.ok:
        environ.report(ollama)
        return EXIT_ERROR

    if not containers.is_built(stack):
        print(
            f"\ncarbonara: first cook with {stack.name} in Docker, building its image"
        )
        if not containers.build(stack):
            print(f"carbonara: could not build the {containers.image(stack)} image")
            return EXIT_ERROR

    if args.telemetry:
        print("carbonara: --telemetry, leaving the framework's own defaults alone")

    return containers.run(stack, overrides(args), telemetry=args.telemetry)
