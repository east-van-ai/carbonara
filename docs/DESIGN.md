# DESIGN

Design notes for `carbonara`. Decisions and the reasoning under them. The
command surface, and the decisions made about it, live in CLI.md.

## What this consolidates

Four standalone demos of the same scenario, each built on a different agent
stack: `crewai`, `langgraph`, `smolagents`, and a no-framework plain Python
version. Every one is a single file of roughly two hundred lines. Every one
talks to a local Ollama model. The scenario is a kitchen: a dispatcher takes a
plain English order, an expeditor reasons out which workers to call and in what
sequence, and the workers each do one job.

Four repos meant four clones, four virtual environments, and four sets of
instructions to run what is fundamentally one demo shown four ways. `carbonara`
is the single entry point over all four.

## The constraint that decides everything

`crewai` runs on Python 3.12. The other three run on 3.14.

This is not a preference. `crewai` declares `requires-python = "<3.14,>=3.10"`,
an explicit upper bound rather than an untested gap, so 3.14 is refused at
install time. Checked against 1.15.28 on 2026-10-15.

This is not a dependency conflict. It is an interpreter conflict, and no
arrangement of extras, markers, or resolver hints spans it. One process cannot
be both interpreters. So the four stacks were never going to share an
environment, and the question was only ever what kind of separation.

Everything below follows from that one fact.

## The dispatcher never imports a framework

`carbonara` itself depends on the standard library and nothing else. It does
not import `crewai`, `langgraph`, `smolagents`, or `ollama`. It locates an
interpreter, hands it a script, and gets out of the way.

That keeps the dispatcher on 3.14 while `crewai` stays on 3.12. It also means
adding a fifth stack cannot break the four already there, because nothing in
the tool's own environment moves when a stack's environment changes.

## One environment per stack

Each stack gets a virtual environment of its own, built from the interpreter
its `python-version` file names, populated from its own pinned requirements.

Environments live outside the repo, under
`${XDG_DATA_HOME:-~/.local/share}/carbonara/venvs/<stack>/`. An installed
command should run from any directory, and a checkout is not guaranteed to be
present or writable once the tool is installed with `pipx`. Keeping the
environments in a user data directory means `carbonara cook-with crewai`
behaves the same whether it was installed from a tag or from a working tree.

Interpreter discovery asks three places, because each one misses on its own.

A pyenv shim is version-gated, not merely present or absent. `python3.12` sits
on `PATH` and still refuses to run whenever the current directory's
`.python-version` names something else. That is not a hypothetical: this
repo pins 3.14, so `PATH` alone reports 3.12 missing on a machine that has it
installed. `pyenv prefix 3.12` answers from what is installed instead, and
resolves a partial version, so it is asked as well. `sys.executable` is the
third, for a `pipx` install sitting on an interpreter `PATH` never names.

Every candidate is then run and asked what version it is. Finding a name is not
the same as finding a working interpreter, and a shim that resolves somewhere
unexpected should be caught rather than trusted.

## Docker, a second way to run

`--docker` runs a stack in a container instead of a virtual environment. The
image does the venv's job, Ollama stays on the host, and the container sits on
a locked network with no route out. A relay forwards Ollama's port, and
nothing else gets through. DOCKER.md holds the design, the relay, and what the
lock cannot stop.

## Stacks are data, not packages

The four implementations sit under `src/carbonara/stacks/<name>/` as scripts
beside their requirements files. They are never imported. They are arguments
passed to another interpreter.

This is why the directory holding `crewai`'s implementation does not need to be
a valid Python package name, and why nothing in the dispatcher may reach into
one with an import. Crossing that line silently reintroduces the interpreter
conflict the whole design exists to avoid.

There is a second reason to leave them whole, and it outlives the first. The
four repeat each other heavily: the same doers, the same colours, the same
shape of prompt. Factoring that into a module they all import is the obvious
tidy, and it would destroy the only thing the four are for. Reading them side
by side is the product. What a framework makes you write is precisely what a
shared base would hide, so the repetition is carrying the argument rather than
sitting there as debt. Nothing in a stack imports carbonara, and no stack
imports another.

## Configuring a stack across the subprocess boundary

Each demo carries its model, temperature, and order as literals at the top of
the file, meant to be edited live during a talk. The CLI needs to set the same
knobs, and it cannot set them by import.

They pass as environment variables: `CARBONARA_MODEL`,
`CARBONARA_TEMPERATURE`, `CARBONARA_ORDER`, `CARBONARA_STREAM_DELAY`, and
`CARBONARA_OLLAMA_URL`. Each stack reads them with its literal as the default,
so a stack script still runs correctly on its own with no environment set. The
demo stays editable by hand, which is the point of keeping those literals at
the top.

## The expeditor's plan survives a decorated answer

Two stacks read their plan out of prose. `no-framework` and `langgraph` both
ask the expeditor for `CALL <doer>: <instruction>` lines and parse what comes
back. The other two never parse anything: `smolagents` has the model write
Python, and `crewai` wires its agents together in a fixed sequence.

Models decorate. The same correct plan arrives as a numbered list, with the
doer name in bold, or both at once. A parser that requires the line to begin
with `CALL` drops all of it, and the demo then apologises for a plan the model
got right.

So list markers and asterisks come off the line before the match. The match
itself stays anchored to the start, because a doer named in passing partway
through a sentence is not a call. The registry lookup and the de-duplication
after it are what keep the plan honest, so widening what matches cannot put a
step in the plan that is not a doer.

The default is a chat model, and chat models decorate. A coder model emits bare
literal lines instead, so a parser written against that habit leans on it
without saying so. Reading both is what keeps the model behind the expeditor a
choice rather than a constraint.

Each stack keeps its own copy of this. Sharing it would mean one stack
importing another, which is the comparison this repository exists to make.

## Telemetry is off unless it is asked for

Two of the four stacks call home with their own defaults: crewai sends its own
telemetry, and smolagents fetches a price list through LiteLLM. CALLS-HOME.md
holds the measurement: what each stack reaches, which library makes the call,
the switch that stops it, and how to measure it again. This section holds the
decision.

The demo promises to run entirely on the user's own machine, and a demo run in
front of an audience is the worst possible place to discover otherwise.

### The decision

`carbonara` sets every known telemetry switch to off before it runs any stack.
crewai files its consent answer under the name of the working directory, so
`carbonara` also pins `CREWAI_STORAGE_DIR` to a fixed name, and the answer
stops depending on where the user is standing. `--telemetry` on `cook-with`
leaves all of it unset, so upstream defaults apply and the frameworks behave
as their own documentation says.

Opt-in rather than opt-out, because staying on the user's machine is the
stronger commitment and because the alternative is a surprise network call
during a talk.

crewai's first-run tracing prompt needs one more step, since it reads a
consent file rather than the environment. `carbonara` writes
`trace_consent: false` into the consent file when the key is absent, and never
overwrites an answer already there. So the prompt never appears, and a
deliberate yes recorded earlier still stands.

The alternative was to leave the prompt alone and only fix the storage key, so
the question is asked once and the answer sticks. It is the more transparent
option and it loses on where this runs: a y/n about uploading data, appearing
mid-demo, is not a fair place to ask anyone anything.

None of this is hidden. `carbonara list` carries a CALLS HOME column naming
which stacks would reach the network, and turning them loose again is one
documented flag.

Every cook also prints the command it runs, ready to paste into a shell, so
the switches are on screen, not only in a document. The consent file stays
off screen. It is written before the run, so a pasted command on a fresh
machine can still meet crewai's prompt.

The column counts what a stack does, observed with the frameworks' own
defaults. What a stack could do, given a setting the demo never makes, is
recorded in CALLS-HOME.md and never counted.

## The PyPI name is squatted, and it does not matter

`carbonara` on PyPI is an unrelated placeholder, version 0.1.1, summary "Add
your description here".

The distribution keeps the name anyway, because PyPI is not where this goes.
Releases here are orphan tags on GitHub, carved out by `weed-out` and installed
with `pipx` from the repository. Renaming the distribution to dodge a stub
would buy nothing and cost the one thing worth keeping, which is that the
command, the repository, and the package all answer to the same word.

The install line names the repository rather than the package index, so nobody
following it lands on the placeholder.

## Layout

```text
src/carbonara/
    cli.py             banner, command table, slot reading, main
    args.py            parser, exit codes, type callables, installed_version
    cli_list.py        one module per command word, each holding that
    cli_prep.py        command's own documentation, USAGE line, and run()
    cli_cook_with.py
    registry.py        the four stacks as data: name, interpreter, paths
    environ.py         interpreter discovery, venv building, readiness
    containers.py      Docker mode: images, the locked network, the relay
    docker/            the one Dockerfile, shipped as package data
    stacks/            the four implementations, shipped as package data
```

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
