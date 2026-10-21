"""Helpers more than one command uses: the stack rows `list` and the bare pages print."""

from . import containers, environ, registry


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


def stack_table(docker=None):
    """Return the heading and one line per stack, as `list` prints them.

    `docker` is a check already made, so a caller that needs one for itself
    probes Docker once rather than twice.
    """
    if docker is None:
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

    heading = (
        f"  {'STACK':<{width}}  PYTHON  {'ENVIRONMENT':<{state_width}}  "
        f"{'IMAGE':<{image_width}}  CALLS HOME"
    )
    lines = [heading]
    for name, version, condition, built, calls, summary in rows:
        lines.append(
            f"  {name:<{width}}  {version:<6}  {condition:<{state_width}}  "
            f"{built:<{image_width}}  {calls:<10}  {summary}"
        )
    return "\n".join(lines)
