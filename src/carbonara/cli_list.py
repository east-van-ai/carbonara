"""What `carbonara list` prints: every stack's state, then Ollama's and Docker's.

list takes no STACK and no options. Its bare form is already a complete
command line, so it runs rather than documenting itself.
"""

from . import containers, environ, registry, shared

HELP = "show the stacks and their state"
USAGE = "carbonara list"
SLOTS = ()


def table():
    """Return every stack's state, then Ollama's and Docker's, as printed."""
    docker = containers.check_docker()
    lines = ["", shared.stack_table(docker)]

    ollama = environ.check_ollama()
    lines.append("")
    if ollama.ok:
        lines.append(
            f"  ollama at {environ.ollama_base_url()} has {registry.DEFAULT_MODEL}"
        )
    else:
        lines.append(f"  {ollama.problem}")
        lines.append(f"  try: {ollama.fix}")
    if docker.ok:
        lines.append("  docker is running; --docker cooks behind a locked network")
    else:
        lines.append(f"  {docker.problem}")
        lines.append(f"  try: {docker.fix}")
    lines.append("")
    lines.append(f"  environments live in {environ.venvs_root()}")
    lines.append(
        f"  {len(registry.PHONES_HOME)} of the {len(registry.NAMES)} stacks reach "
        "the network on their own account."
    )
    lines.append(
        "  carbonara silences all of them; --telemetry on a cook hands it back"
    )
    lines.append("")
    return "\n".join(lines)
