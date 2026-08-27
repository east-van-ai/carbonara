# DESIGN

Design notes for `carbonara`. Decisions and the reasoning under them. The
README draws the finished shape; this file says why that shape and not another.

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
install time. Checked against 1.15.17 on 2026-08-26.

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

`prep` installs from `requirements-pinned.txt`. This is demonstration software
that gets run in front of people, so a run that behaves the way it behaved
yesterday is worth more than a run on the newest resolvable tree. `--latest`
installs from the unpinned `requirements.txt` for anyone deliberately testing
against current releases.

## Stacks are data, not packages

The four implementations sit under `src/carbonara/stacks/<name>/` as scripts
beside their requirements files. They are never imported. They are arguments
passed to another interpreter.

This is why the directory holding `crewai`'s implementation does not need to be
a valid Python package name, and why nothing in the dispatcher may reach into
one with an import. Crossing that line silently reintroduces the interpreter
conflict the whole design exists to avoid.

The consequence for packaging: these files ship as package data, declared
explicitly. Automatic package discovery will not find them, because they are
not packages.

There is a second reason to leave them whole, and it outlives the first. The
four repeat each other heavily: the same doers, the same colours, the same
shape of prompt. Factoring that into a module they all import is the obvious
tidy, and it would destroy the only thing the four are for. Reading them side
by side is the product. What a framework makes you write is precisely what a
shared base would hide, so the repetition is carrying the argument rather than
sitting there as debt. Nothing in a stack imports carbonara, and no stack
imports another.

## Configuring a stack across the subprocess boundary

Each demo currently carries its model, temperature, and stream delay as
literals at the top of the file, meant to be edited live during a talk. The CLI
needs to set the same knobs, and it cannot set them by import.

They pass as environment variables: `CARBONARA_MODEL`,
`CARBONARA_TEMPERATURE`, `CARBONARA_STREAM_DELAY`, and `CARBONARA_ORDER`. Each
stack reads its own with a default equal to the literal it carries today, so a
stack script still runs correctly on its own with no environment set. The demo
stays editable by hand, which was the point of putting those literals at the
top in the first place.

## Telemetry is off unless it is asked for

Three of the four stacks phone home by default. The README promises the
opposite, and a demo run in front of an audience is the worst possible place
to discover otherwise.

What is actually there, in `crewai` 1.14.7:

- Anonymous telemetry posts to `https://telemetry.crewai.com:4319/v1/traces`.
  It is always on and it never asks. Any of `OTEL_SDK_DISABLED`,
  `CREWAI_DISABLE_TELEMETRY`, or `CREWAI_DISABLE_TRACKING` set to `true`
  turns it off.
- Execution tracing is separate. It prompts after the first run completes,
  and on yes it uploads that run's traces. The answer is stored as
  `trace_consent` in `.crewai_user.json`.

`smolagents` reaches Hugging Face and honours `HF_HUB_DISABLE_TELEMETRY`.
`langgraph` honours `LANGCHAIN_TRACING_V2` and `LANGSMITH_TRACING`, both of
which need a key and are off unless set. The no-framework stack talks to
nothing but Ollama, which is the point of it.

Two upstream details make this worse than a default nobody likes.

The consent file is keyed to the working directory. `crewai_core.paths`
resolves its storage name as `os.environ.get("CREWAI_STORAGE_DIR",
Path.cwd().name)`, so the answer is filed under the basename of wherever the
command was run. Declining in one directory and running from another asks
again, and for a tool installed with `pipx` and run from anywhere, that means
the question never stays answered.

Tracing has no off switch in the environment. `CREWAI_TRACING_ENABLED` is
read as `in ("true", "1")`, so it can only turn tracing on. Nothing set there
turns it off. The file is the only control, and the check is
`data.get("trace_consent", False) is not False`, an identity comparison, so
only a literal JSON `false` disables it. A `null` left in that slot enables
tracing.

### The decision

carbonara sets every known telemetry switch to off before it runs any stack,
and pins `CREWAI_STORAGE_DIR` to a fixed name so the answer stops depending on
where the user is standing. `--telemetry` on `cook-with` leaves all of it unset,
so upstream defaults apply and the frameworks behave as their own
documentation says.

Opt-in rather than opt-out, because the promise in the README is the stronger
commitment and because the alternative is a surprise network call during a
talk.

Tracing needs one more step, since no environment variable can disable it.
carbonara writes `trace_consent: false` into the consent file when the key is
absent, and never overwrites an answer already there. So the prompt never
appears, and a deliberate yes recorded earlier still stands.

The alternative was to leave the prompt alone and only fix the storage key, so
the question is asked once and the answer sticks. It is the more transparent
option and it loses on where this runs: a y/n about uploading data, appearing
mid-demo, is not a fair place to ask anyone anything.

None of this is hidden. `carbonara list` carries a CALLS HOME column naming
which stacks would reach the network, and turning them loose again is one
documented flag.

## The PyPI name is squatted, and it does not matter

`carbonara` on PyPI is an unrelated placeholder, version 0.1.1, summary "Add
your description here".

The distribution keeps the name anyway, because PyPI is not where this goes.
Releases here are orphan tags on GitHub, carved out by `weed-out` and installed
with `pipx` from the repository. Renaming the distribution to dodge a stub
would buy nothing and cost the one thing worth keeping, which is that the
command, the repository, and the package all answer to the same word.

The install line names the repository rather than the package index, so nobody
following the README lands on the placeholder.

## Command surface

```text
carbonara list
carbonara prep STACK [--latest]
carbonara cook-with STACK [--order TEXT] [--model NAME] [--temperature N]
carbonara cook-with STACK [--stream-delay N] [--telemetry]
```

The original sketch was `carbonara crewai`, with the stack as the command word.
That form cannot work here, because a command word and nothing else is reserved
for documentation. `carbonara crewai` can only ever print help, never cook
anything. Making the stack the main argument of a verb keeps the reserved form
free and keeps the stack list as data rather than as vocabulary.

The verb is `cook-with` rather than `run`, and it earns the extra syllable.
`carbonara cook-with crewai` reads as a sentence, and `carbonara cook-with
no-framework` reads as the joke it is. The scenario is a kitchen throughout,
the roles are dispatcher and expeditor and doers, so a command word out of the
same world costs nothing and tells the reader what kind of tool this is before
they run it.

`carbonara list` names the four stacks, the interpreter each wants, and whether
its environment is built. It is the command that answers "why did that fail".

## A command with nothing to name

The house rule reserves a bare command word for documentation, on the reasoning
that the user typed something incomplete and should get help rather than an
error. `carbonara list` takes no argument, so there is nothing incomplete about
it, and applying the rule literally would leave `list` with no way to run.

So a command that takes no main argument runs on its bare form. The divergence
is deliberate and narrow: `list` is the only such command, and a stray word
after it is still a usage error. Its documentation lives in the banner, which
is where a one-line command belongs.

## Readiness

Two things fail outside the tool's control, and both fail the same way for
every stack: the interpreter a stack needs is not installed, and Ollama is not
reachable or does not have the model pulled.

These are readiness failures, not grammar failures, so they print no usage
line. Each names the exact command that fixes it, `pyenv install 3.12` or
`ollama pull qwen2.5-coder:3b`. `cook-with` checks both before it builds
anything, so a missing model surfaces in a second rather than after an
install.

## Exit codes

0 for success and for documentation, 1 for the tool's own errors including
readiness failures, 2 for argparse. Standard for the toolchain.

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
    stacks/            the four implementations, shipped as package data
```

## Use of AI

Both the use of AI and its disclosure are deliberate. Code and
documentation in this project are written in collaboration with
Artificial Intelligence (AI). The division of labour: the AI explores,
challenges assumptions and edge cases, and drafts; the human
initiates, drafts the designs, explores alongside the AI, reviews
every change, and decides what gets committed.

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

Copyright (c) 2026 Go Nakamaru
