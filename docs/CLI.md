# CLI

The command surface of `carbonara`: the grammar, what each command word answers,
and the exit codes. The model under it, and the reasoning for that model, is in
DESIGN.md.

## Command surface

```text
carbonara list
carbonara prep STACK (--venv | --docker) [--latest]
carbonara cook-with STACK (--venv | --docker) [--order TEXT] [--model NAME]
carbonara cook-with STACK (--venv | --docker) [--temperature N]
carbonara cook-with STACK (--venv | --docker) [--stream-delay N] [--telemetry]
carbonara clean STACK (--venv | --docker)
carbonara version
```

The stack is the main argument of a verb, never the command word. A command
word and nothing else is reserved for documentation, so `carbonara crewai` could
only ever print help, never cook anything. Keeping the stack out of the command
position keeps the reserved form free, and keeps the stack list as data rather
than as vocabulary.

The verb is `cook-with` rather than `run`, and it earns the extra syllable.
`carbonara cook-with crewai` reads as a sentence, and `carbonara cook-with
no-framework` reads as the joke it is. The scenario is a kitchen throughout,
the roles are dispatcher and expeditor and doers, so a command word out of the
same world costs nothing and tells the reader what kind of tool this is before
they run it.

Every command word is a verb, and a command added later takes one too. `menu`
was considered for `list` and rejected because it is a noun. The metaphor earns
its place only where it also describes the action.

`carbonara list` names the four stacks, the interpreter each wants, and whether
its environment and its Docker image are built. It is the command that answers
"why did that fail", so its name stays plain. A charming name costs most at
exactly the moment someone is lost.

## A command with nothing to name

The house rule reserves a bare command word for documentation, on the reasoning
that the user typed something incomplete and should get help rather than an
error. `carbonara list` takes no argument, so there is nothing incomplete about
it, and applying the rule literally would leave `list` with no way to run.

So a command that takes no main argument runs on its bare form. The divergence
is deliberate and narrow: `list` is the only such command, and a stray word
after it is still a usage error. The banner describes it, since that is where
a one-line command belongs. `carbonara list --help` prints its usage.

`version` takes no argument either, and needs no exception. What it prints is
documentation, which is what the bare form is reserved for. A stray word after
it is a usage error, the same as after `list`.

```text
$ carbonara version extra
carbonara: version takes nothing after it: 'extra'
Usage: carbonara version
```

## Positions are decided, not inferred

STACK is read off the front of the command line: the words after the command
word, up to the first flag. Whatever argparse resolved from anywhere else is
discarded.

On Python 3.14, argparse fills an optional positional from a word that comes
after a flag. Left alone, `carbonara prep --latest crewai` would parse with
`crewai` as the stack, and the grammar the tool accepts would drift away from
the one documented above. Reading the slot directly keeps the two the same.

```text
$ carbonara prep --latest crewai
carbonara: prep needs STACK
Usage: carbonara prep STACK (--venv | --docker) [--latest]
```

A bare word after a flag is a stray, the same as one after STACK. The command
refuses it and never runs. Without that check, `clean crewai --docker extra`
would quietly drop `extra` and remove the image.

```text
$ carbonara clean crewai --docker extra
carbonara: clean takes nothing after STACK: 'extra'
Usage: carbonara clean STACK (--venv | --docker)
```

## Help pages

Bare `carbonara` prints the banner, then `carbonara --help`. A bare command word
prints that command's page: a few paragraphs on what it does, then argparse's
own help for it. Every flag and every default is written once, in the parser,
so a page cannot document a flag the command rejects. Help is never coloured.

The pages of `prep`, `cook-with`, and `clean` also carry the stack table from
`list`: each stack's interpreter, its environment and its image, and whether it
calls home. The bare word is typed right before picking a stack, so the page
answers which one is ready. It looks at Docker to fill the IMAGE column, and a
daemon that hangs holds the page up to 20 seconds. The page still exits 0
whatever it finds. `--help` stays argparse's own text, with no table.

The positional is STACK, not a path, so every page closes on a `stack:` heading.
The defaults the help names are the ones the stack scripts read. `--stream-delay`
says it reaches no-framework only, because the other three scripts never read
it.

## Pinned requirements, and `--latest`

`prep` installs from `requirements-pinned.txt`. This is demonstration software
that gets run in front of people, so a run that behaves the way it behaved
yesterday is worth more than a run on the newest resolvable tree. `--latest`
installs from the unpinned `requirements.txt` for anyone deliberately testing
against current releases.

## The mode: `--venv` or `--docker`

`prep`, `cook-with`, and `clean` each take exactly one mode. `--venv` acts on
the stack's virtual environment, and `--docker` on its image. On `cook-with`,
a stack not yet prepped in that mode is prepped first. `--latest` means the
same thing in both modes. So does `--telemetry`: it hands the frameworks their
own defaults, and under `--docker` one of those defaults is an open network.
Without it, the container is locked.

Neither mode is a default. A command that names its mode reads the same however
many ways to run there are, and a default would quietly pick one of them. A
missing mode is a slip, refused like a missing STACK and checked after it.
Nothing runs. Both modes together is argparse's error, exit 2.

```text
$ carbonara cook-with crewai
carbonara: cook-with needs --venv or --docker
Usage: carbonara cook-with STACK (--venv | --docker) [--order TEXT] [--model NAME] [--temperature N] [--stream-delay N] [--telemetry]
```

The mode is a flag, not a command word, because it changes how a command runs,
not what it does. `list` takes neither flag. It reports both modes side by
side, ENVIRONMENT and IMAGE, so there is nothing for a flag to choose.

## `clean`

`clean` removes one stack's station, so the next `prep` builds from scratch
rather than on top of what is there. Under `--venv` that is the stack's venv.
Under `--docker` it is the stack's image and the locked network. The network
outlives every cook, and this is the way to remove it. The relay image stays,
since a fresh pull brings back the same bytes.

It takes one stack and asks nothing. A form that cleans every stack would put
four stations behind one typo, and four calls cost little. Something already
gone is reported as `nothing to clean`, exit 0, so a second run changes nothing.

Docker refuses to remove an image or the network while a cook is using it.
`clean` passes the refusal on and exits 1. It never forces a removal. Each
`docker` command it runs is printed first, as a cook's is. A venv is removed in
Python, so `clean` prints the path it removed, not a shell line.

crewai's consent file is never touched.

## A cook shows its command first

Before a stack starts, `cook-with` prints `carbonara: running` and the command
it is about to run, one option per line, quoted for a shell. In a venv, that is
an `env` line: the variables carbonara adds, then the interpreter and the
script. Under `--docker`, it is the `docker run` line. A locked cook prints the
relay's commands around it: the relay's start and its connection to the locked
network before, and its removal after. An image build prints its `docker build`
line the same way.

It prints on every cook, with no flag to ask for it or to turn it off. Pasted
into a shell, it cooks the same stack the same way, without carbonara.

## Readiness

Two things fail outside the tool's control, and both fail the same way for
every stack: the interpreter a stack needs is not installed, and Ollama is not
reachable or does not have the model pulled. Under `--docker`, a third: Docker
is not installed or not running. Its fix is `start Docker Desktop`, and the
interpreter check is skipped, since the image brings its own Python.

These are readiness failures, not grammar failures, so they print no usage
line. Each names the exact command that fixes it: `pyenv install 3.12`,
`ollama serve`, or `ollama pull hf.co/CohereLabs/tiny-aya-global-GGUF:Q4_K_M`.
`cook-with` checks both before it builds anything, so a missing model surfaces
in a second rather than after an install.

A failure after the first write is a runtime failure. That covers a build that
broke, a venv that could not be removed, and Docker refusing an image, the
network, or the relay. The message names what could not be done, with Docker's
own words where there are some. It prints no usage line. `clean --docker` tries
the network even after the image is refused, and reports both refusals.

## Exit codes

Standard for the toolchain.

| Code | When |
| --- | --- |
| 0 | Success, or documentation from a bare command word. |
| 1 | Its own errors: a missing or stray word, no mode, a failed check or run. |
| 2 | argparse refused the line: unknown words or flags, a bad value, both modes. |

Once a stack's script starts, `cook-with` exits with that script's own code,
passed through unchanged.

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
