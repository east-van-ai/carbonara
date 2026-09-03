# carbonara

Four AI agent projects, merged into one command.

The same demo exists four times over, once per agent stack, each built as a
standalone project in a repository of its own. `carbonara` brings all four
under a single CLI. Their implementations are vendored here whole, so this is
a merge of finished work rather than a fresh start, and it arrives with four
projects' worth of code already in it.

| Stack | What it is | Calls home |
| --- | --- | --- |
| `crewai` | Role-based agents with a crew and tasks | yes |
| `langgraph` | A state graph, nodes and edges | yes |
| `smolagents` | Minimal agents over LiteLLM | yes |
| `no-framework` | Plain Python. A prompt and a registry | no |

What they all build is the same kitchen. A dispatcher takes a plain English
order. It knows nothing about cooking. An expeditor, powered by a local LLM,
reasons through the job, picks the right workers, and puts them in the right
order. The workers each do one thing and report back.

The interesting part is that nobody hardcoded the sequence. The model works out
that the guanciale can render while the pasta boils, and that the egg sauce
must not meet a hot pan. Watching it reason is the demo.

Run the four back to back and the differences between them stop being abstract.

## So you compared them. What did you learn?

That is the question, and it is the only reason to build the same thing four
times. Two of the answers were news.

The first is the calls-home column above. Three of the four reach the network
on their own account, and none of them asks first. The one that stays on your
machine is the one with no framework under it.

Someone who knows `crewai` well knows where its telemetry setting lives. What
they cannot see from inside `crewai` is that the plain Python version has no
setting at all, because it has nothing that would place the call. That only
shows up with all four side by side.

The second shows up when you try to install them together. `crewai` declares
`requires-python <3.14`. The other three want 3.14. Nothing warns you until
those two demands are in the same room, and by then you are not comparing
frameworks any more, you are negotiating with a resolver.

Plenty of people are expert in a framework. Far fewer are expert in frameworks,
plural. That gap is most of what this repository is for.

`carbonara` silences all three callers before anything starts, and gives every
stack an interpreter of its own. Both are below.

If that made you want to read them rather than run them, they are four files,
one per stack, in `src/carbonara/stacks/`. Around 200 lines each and nothing is
shared between them, on purpose. Factor the common parts out and the comparison
goes with it.

## Run it

```bash
carbonara cook-with no-framework
```

The first run of a stack builds its environment, then runs the demo. After
that it just runs.

Give it a different order, or turn up the chaos:

```bash
carbonara cook-with langgraph --order "carbonara for six, one without cheese"
```

```bash
carbonara cook-with crewai --temperature 0.8
```

Near zero keeps the plan stable. Push it up and the expeditor starts
improvising, which is either the best or the worst part of the demo depending
on the audience.

## What you will see

```text
[DISPATCHER]  received order: "make me a carbonara"

[EXPEDITOR]   thinking about: "make me a carbonara"
              ... reasoning trace, streamed token by token ...

[DOER boil_pasta]    Boil 200g spaghetti to al dente
[DOER boil_pasta]    Spaghetti is al dente and drained, standing by.

[DOER fry_guanciale] Render guanciale until crisp
[DOER fry_guanciale] Guanciale is crisp, fat rendered into the pan.

... and so on through to combine ...

[DISPATCHER]  Your carbonara is ready. Silky, rich, no scrambled eggs.
```

## The four stacks do not get along

`crewai` needs Python 3.12. The other three need 3.14. That is not a conflict a
resolver can settle, so `carbonara` does not try. Each stack gets its own
interpreter and its own virtual environment, and the CLI itself imports none of
them. It finds the right Python, hands it the right script, and steps back.

You never see any of this unless something is missing, and then it tells you
exactly which command fixes it.

```bash
carbonara list
```

That prints the four stacks, the interpreter each one wants, and whether its
environment is ready.

## Requirements

- [Ollama](https://ollama.com) running locally
- Cohere's `tiny-aya` pulled:
  `ollama pull hf.co/CohereLabs/tiny-aya-global-GGUF:Q4_K_M`
- Python 3.14 for `carbonara` itself
- Python 3.12 available for the `crewai` stack

Everything runs on your own machine. No API keys, no cloud, no per-token
billing while you rehearse.

That includes telemetry. Three of the four frameworks phone home by default,
and one of them asks mid-demo whether it may upload the run. `carbonara` turns
every switch they honour off before it starts anything, and declines the
tracing prompt so it never interrupts. Nothing here is hidden: `carbonara list`
says so, and `--telemetry` on a cook hands the frameworks back their own
defaults.

## Install, or clone

Two doors, and it depends what you came for.

To watch it run:

```bash
pipx install git+https://github.com/east-van-ai/carbonara.git
```

Not from PyPI. The `carbonara` package there is an unrelated placeholder that
has nothing to do with this.

To read the four side by side:

```bash
git clone https://github.com/east-van-ai/carbonara.git
```

Then open `src/carbonara/stacks/`. Four directories, one file each, same
kitchen four ways. `no-framework` is the one to read first, because it shows
the mechanism with nothing in front of it, and the other three are best read as
answers to it.

## Use of AI

This project is built with Artificial Intelligence (AI), deliberately
and in the open. Code and documentation are written in collaboration
with remote and local AI; design decisions, code review, and final
judgement stay human.

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

Copyright (c) 2026 Go Nakamaru
