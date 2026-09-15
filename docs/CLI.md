# CLI

The command surface of `carbonara`: the grammar, what each command word answers,
and the exit codes. The model under it, and the reasoning for that model, is in
DESIGN.md.

## Command surface

```text
carbonara list
carbonara prep STACK [--latest]
carbonara cook-with STACK [--order TEXT] [--model NAME] [--temperature N]
carbonara cook-with STACK [--stream-delay N] [--telemetry]
carbonara version
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

Every command word is a verb, and a command added later takes one too. `menu`
was considered for `list` and rejected because it is a noun. The metaphor earns
its place only where it also describes the action.

`carbonara list` names the four stacks, the interpreter each wants, and whether
its environment is built. It is the command that answers "why did that fail", so
its name stays plain. A charming name costs most at exactly the moment someone
is lost.

## A command with nothing to name

The house rule reserves a bare command word for documentation, on the reasoning
that the user typed something incomplete and should get help rather than an
error. `carbonara list` takes no argument, so there is nothing incomplete about
it, and applying the rule literally would leave `list` with no way to run.

So a command that takes no main argument runs on its bare form. The divergence
is deliberate and narrow: `list` is the only such command, and a stray word
after it is still a usage error. Its documentation lives in the banner, which
is where a one-line command belongs.

`version` takes no argument either, and needs no exception. What it prints is
documentation, which is what the bare form is reserved for. A stray word after
it is a usage error, the same as after `list`.

```text
$ carbonara version extra
carbonara: version takes no arguments: 'extra'
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
Usage: carbonara prep STACK [--latest]
```

## Pinned requirements, and `--latest`

`prep` installs from `requirements-pinned.txt`. This is demonstration software
that gets run in front of people, so a run that behaves the way it behaved
yesterday is worth more than a run on the newest resolvable tree. `--latest`
installs from the unpinned `requirements.txt` for anyone deliberately testing
against current releases.

## Readiness

Two things fail outside the tool's control, and both fail the same way for
every stack: the interpreter a stack needs is not installed, and Ollama is not
reachable or does not have the model pulled.

These are readiness failures, not grammar failures, so they print no usage
line. Each names the exact command that fixes it, `pyenv install 3.12` or
`ollama pull hf.co/CohereLabs/tiny-aya-global-GGUF:Q4_K_M`. `cook-with` checks
both before it builds anything, so a missing model surfaces in a second rather
than after an install.

## Exit codes

Standard for the toolchain.

| Code | When |
| --- | --- |
| 0 | Success, or documentation from a bare command word. |
| 1 | The tool's own errors: a misplaced or stray word, a readiness failure. |
| 2 | argparse refused the line: an unknown stack or flag, or an abbreviation. |

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
