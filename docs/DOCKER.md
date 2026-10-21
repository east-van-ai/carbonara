# Docker

`--docker` runs a stack in a container, and `--venv` in a virtual environment.
The point is to show the demo works both ways, so neither mode replaces the
other. This file holds the image, the locked network, the relay to Ollama, and
what the lock cannot stop.

## The image does the venv's job

Each stack gets one image, `carbonara-<stack>`, built on the official
`python:<version>-slim` image for the version its `python-version` file names.
Its requirements install straight into that Python. A venv inside the image
would only repeat the separation the image already gives.

One Dockerfile builds all four, and the image holds dependencies only. The
script is mounted read-only at run time, the way a venv holds dependencies and
the script comes from the package. So editing a stack script needs no rebuild,
in either mode.

Ollama stays on the host. Docker on macOS cannot reach the GPU, so a model in
a container would run on the CPU alone. Starting a container costs about a
quarter of a second, so a cook takes as long in Docker as in a venv. The
model is the time.

## The network is locked

A stack container sits on `carbonara-locked`, a Docker network created with
`--internal`. A container there has no route out. A lookup of any outside name
fails at once, and so does a connection to a bare IP address. No timeout, no
wait.

So under `--docker`, a switch nobody listed has nowhere to send anything. The
switches carbonara sets in a venv are still set, along with crewai's consent
file, mounted where crewai looks for it on Linux. The lock is a backstop, not
the only defence.

`--telemetry` opens the network. The container goes on Docker's default
network, with a route out, and the switches are left unset. The flag keeps one
meaning in both modes: hand the frameworks their own defaults, and under
`--docker` one of those defaults is a way out.

## A relay reaches Ollama

Ollama is on the host, and the locked network cannot reach the host. So each
locked cook starts a relay: a small `alpine/socat` container, pinned by digest,
that sits on both the default network and the locked one. It forwards one
port, Ollama's, to the host. The stack is handed `http://ollama.internal:11434`
and never learns where Ollama really is.

The relay belongs to one cook. It starts before the stack and is removed after,
including on Ctrl-C and SIGTERM, so a cook leaves no container behind. Only
SIGKILL leaves one, since nothing runs after it. The relay is named for its
carbonara's process ID, so `clean --docker` can tell a leftover from a live
one. The network costs nothing and stays. `carbonara clean STACK --docker`
removes it with the stack's image and any leftover relay, and the next locked
cook makes it again. The relay image stays: it is pinned by digest, so a fresh
pull would bring back the same bytes.

The relay's name on the locked network is `ollama.internal`, and the suffix is
load-bearing. Ollama checks the `Host` header of every request and answers 403
to a plain name like `ollama`. Names under `.internal` and `.localhost` pass.
`host.docker.internal` is the one name under `.internal` that cannot be used.
Docker Desktop answers it itself, with an address the locked network cannot
reach, and the call hangs for 30 seconds.

Like every cook, a locked one prints its commands before running them: the
relay, its connection to the locked network, then the stack. After the cook it
prints the relay's removal, `docker rm --force`, and runs it. The relay never
stops on its own, so this is what ends it. Pasted in order into a shell, the
four commands rebuild the lock, cook, and leave nothing running.

## Ctrl-C stays with carbonara

At a terminal, the stack runs with `--tty` alone, never `--interactive`. With
both, Docker puts the terminal in raw mode, and Ctrl-C reaches the container as
a keystroke instead of reaching carbonara. Without `--interactive`, the
container takes no stdin. So crewai's trace-sharing prompt under `--telemetry`
answers no by itself.

## What the lock cannot stop

The relay forwards TCP. It does not read what passes through. So a locked stack
can call any part of Ollama's API, not just chat: list the models, pull a new
one, or delete one. A pull also means Ollama on the host goes to the internet
on the stack's behalf.

This probe shows it. It builds the same lock by hand, then asks from inside:

```bash
docker network create --internal carbonara-locked 2>/dev/null
docker run --detach --rm --name carbonara-probe-relay \
    --add-host host.docker.internal:host-gateway \
    alpine/socat@sha256:fb3862c949af7c79996d0e514ee96128644d840835ed5368eeecb14a869de361 \
    TCP-LISTEN:11434,fork,reuseaddr TCP:host.docker.internal:11434
docker network connect --alias ollama.internal carbonara-locked carbonara-probe-relay
docker run --rm --network carbonara-locked python:3.12-slim python -c '
import json, urllib.request

def call(method, path, body=None):
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request("http://ollama.internal:11434" + path, data, method=method)
    try:
        answer = urllib.request.urlopen(request, timeout=15)
        print(f"{method:6} {path:12} {answer.status} {answer.read(60)}")
    except urllib.error.HTTPError as e:
        print(f"{method:6} {path:12} {e.code} {e.read(60)}")

call("GET", "/api/tags")
call("POST", "/api/pull", {"model": "carbonara-probe-missing", "stream": False})
call("DELETE", "/api/delete", {"model": "carbonara-probe-missing"})
for url in ["https://telemetry.crewai.com", "https://1.1.1.1"]:
    try:
        urllib.request.urlopen(url, timeout=5)
        print(f"{url:30} reached")
    except OSError as e:
        print(f"{url:30} blocked: {e.reason}")
'
docker rm --force carbonara-probe-relay
```

On macOS with Docker Desktop 29.8.0 and Ollama 0.33.3, the probe prints:

```text
GET    /api/tags    200 b'{"models":[{"name":"granite4:3b","model":"granite4:3b","modi'
POST   /api/pull    500 b'{"error":"pull model manifest: file does not exist"}'
DELETE /api/delete  404 b'{"error":"model \'carbonara-probe-missing\' not found"}'
https://telemetry.crewai.com   blocked: [Errno -3] Temporary failure in name resolution
https://1.1.1.1                blocked: [Errno 101] Network is unreachable
```

All three Ollama calls are answered by Ollama. The pull asks for a model that
does not exist, so nothing downloads. The error still says Ollama went to its
registry and came back empty-handed. The delete names a missing model too, and
Ollama says so rather than refusing the call. The outside name and the bare IP
fail at once.

A relay that read each request and passed only chat would close this. It would
need an HTTP proxy with a configuration to pin and keep current, in place of
one socat line. The limit is shown instead. For a demo about who calls home,
the honest lock is the one whose gap is on the page.

Stricter still is a container with no network at all, whose model calls go to
a program on the host that decides what to ask Ollama. That needs the stack to
talk to that program instead of to Ollama. Three of the four stacks are
frameworks that call Ollama themselves, over HTTP, so only a relay leaves them
as they are.

## Linux

Untested. Ollama on Linux listens on `127.0.0.1` by default, out of a
container's reach, so the relay finds nothing to forward to until Ollama
listens on an address the containers can see.

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
