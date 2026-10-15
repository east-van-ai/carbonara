# Calls home

Which of the four stacks reaches the network on its own account, and how that
is known. Everything here is measured, not taken from a framework's
documentation. Each finding holds for the versions below, and a refresh of the
pinned requirements measures it again.

## Measured against

| Package | Version | Released | Measured |
| --- | --- | --- | --- |
| crewai | 1.15.28 | 2026-10-14 | 2026-10-15 |
| langgraph | 1.2.15 | 2026-10-12 | 2026-10-15 |
| smolagents | 1.26.0 | 2026-05-29 | 2026-10-15 |
| LiteLLM, under smolagents | 1.105.1 | 2026-10-14 | 2026-10-15 |
| langsmith, under langgraph | 0.14.9 | 2026-10-15 | 2026-10-15 |

These are the pinned versions. `prep --latest` installs newer ones, and
nothing here speaks for them.

## What each stack does

Each stack cooked with the frameworks' own defaults, `cook-with STACK
--telemetry`, on macOS, with Ollama local and no API keys set.

| Stack | Reaches | Made by | When |
| --- | --- | --- | --- |
| no-framework | nothing | | |
| crewai | `telemetry.crewai.com` | crewai's own telemetry | at 7 s, and at the end |
| langgraph | nothing | | |
| smolagents | `raw.githubusercontent.com` | LiteLLM | at import, 1 s in |

Two of the four. Only one of those calls is telemetry, and it is crewai's own.
The other is not smolagents' at all. LiteLLM, the library smolagents uses to
reach a model, fetches its price list from GitHub as it loads. A local model
has no price, so the fetch buys nothing here.

The lines behind the table, from the logger described below:

```text
   6.64s  telemetry.crewai.com  urllib3 < requests < opentelemetry < crewai_core
  26.89s  telemetry.crewai.com  urllib3 < requests < opentelemetry < crewai_core
   1.09s  raw.githubusercontent.com  httpcore < httpx < litellm < importlib < smolagents < __main__
```

Each call has a switch, and each switch stops its call when set alone:

- crewai: any one of `OTEL_SDK_DISABLED`, `CREWAI_DISABLE_TELEMETRY`, or
  `CREWAI_DISABLE_TRACKING`, set to `true`.
- smolagents: `LITELLM_LOCAL_MODEL_COST_MAP` set to `True`. LiteLLM then reads
  the price list it ships with.

With carbonara's own defaults, telemetry off, every lookup from all four
stacks is local.

## What a stack can do

Read in the source of the pinned versions, not observed. None of it is
counted above, because none of it happens when this demo runs.

- **langgraph** pulls in langsmith through langchain-core. langsmith uploads
  traces to `api.smith.langchain.com` once `LANGSMITH_TRACING` or
  `LANGCHAIN_TRACING_V2` is set to `true`, with a LangSmith key to accept
  them. Nothing turns it on by default.
- **smolagents** reaches the Hugging Face Hub when an agent or a tool is loaded
  from it or pushed to it, or when the model is one the Hub hosts. This demo
  uses a local model and its own tools.
- **huggingface_hub** 1.33.0, under smolagents, defines a `send_telemetry`
  function, and nothing installed in that stack calls it.
  `HF_HUB_DISABLE_TELEMETRY` is still set, and today it has nothing to stop.

## crewai's consent file

crewai has a second channel beside its telemetry: execution tracing. After the
first run, it asks whether it may upload that run's traces. The answer is
stored as `trace_consent` in `.crewai_user.json`.

Tracing itself can be switched off in the environment, with
`CREWAI_TRACING_ENABLED` set to `false` or `OTEL_SDK_DISABLED` set to `true`.
The prompt reads the file instead. Its check is
`data.get("trace_consent", False) is not False`, an identity comparison. Only
a literal JSON `false` counts as a no. A `null` left in that slot enables
tracing.

The file is filed by the working directory. `crewai_core.paths` resolves its
storage name as `os.environ.get("CREWAI_STORAGE_DIR", Path.cwd().name)`. So an
answer given in one directory is asked again from the next. For a tool
installed with `pipx` and run from anywhere, the question never stays
answered.

## How to measure it again

The logger is a `sitecustomize.py`. Python loads that module at startup from
any directory on `PYTHONPATH`, and carbonara passes the environment through to
the stack's interpreter. So the logger runs inside the stack, ahead of every
framework.

```python
"""Log every hostname this process resolves, with when and who, to HOSTLOG."""

import os
import socket
import sys
import sysconfig
import time

_START = time.monotonic()
_STDLIB = (sysconfig.get_paths()["stdlib"], sysconfig.get_paths()["platstdlib"])
_resolve = socket.getaddrinfo


def _callers():
    """Return the top-level packages on the stack, innermost first, stdlib skipped."""
    seen = []
    frame = sys._getframe(2)
    while frame:
        path = frame.f_code.co_filename
        module = frame.f_globals.get("__name__", "?")
        stdlib = path.startswith(_STDLIB) and "site-packages" not in path
        if not stdlib and path != __file__:
            package = module.split(".")[0]
            if package not in seen:
                seen.append(package)
        frame = frame.f_back
    return seen


def _logged(host, *args, **kwargs):
    """Record the lookup, then resolve it as usual."""
    with open(os.environ["HOSTLOG"], "a") as log:
        elapsed = time.monotonic() - _START
        log.write(f"{elapsed:7.2f}s  {host}  {' < '.join(_callers())}\n")
    return _resolve(host, *args, **kwargs)


socket.getaddrinfo = _logged
```

Save it in a directory of its own, then cook with that directory on the path:

```bash
PYTHONPATH=/path/to/logger HOSTLOG=/tmp/hosts.txt carbonara cook-with crewai --telemetry
```

Each line says how many seconds into the run the lookup came, the hostname,
and the packages on the call stack, innermost first. The last package named
is usually the one that wanted the call.

Inside a venv, the platform library path is the venv's own `lib` directory,
and `site-packages` sits under it. That is why the filter checks for
`site-packages` by name. Without it, every third-party frame reads as standard
library, and the chain comes back empty.

A clean log is evidence, not proof. The logger sees only lookups made through
Python's own resolver. A subprocess, a C library with a resolver of its own,
or a connection to a hardcoded IP address would not show.

## Use of AI

Both the use of AI and its disclosure are deliberate. Code and documentation in
this project are written in collaboration with Artificial Intelligence (AI). The
division of labour: the AI explores, challenges assumptions and edge cases, and
drafts; the human initiates, drafts the designs, explores alongside the AI,
reviews every change, and decides what gets committed.

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

Copyright (c) 2026 Go Nakamaru
