# 🍝 carbonara

## Good ingredients. Different chefs. Who makes the best Carbonara?

Three AI agent frameworks and one plain-Python cook enter the kitchen. They get
the same order, the same ingredients, and the same hungry customer. But they
don't cook the same way. Can they plan, delegate, coordinate, and get dinner on
the table?

And more importantly...

**Can you trust what's happening behind the kitchen doors?**

Four cooks. One recipe. One controlled environment. Let's see what happens.

## Meet the cooks

Each cook already had a kitchen of its own. The same demo was built four times,
once per agent stack, each as a standalone project in its own repository. This
project brings all four under one roof and one CLI. Their code comes along
whole. Nothing was rewritten to make the comparison easier.

| Stack | What it is | Calls home |
| --- | --- | --- |
| `crewai` | Role-based agents with a crew and tasks | yes |
| `langgraph` | A state graph, nodes and edges | no |
| `smolagents` | Minimal agents over LiteLLM | yes |
| `no-framework` | Plain Python. A prompt and a registry | no |

Every cook runs the same kitchen. A dispatcher takes the order in plain
English, and knows nothing about cooking. An expeditor, a small LLM running on
your machine, reasons through the job, picks the right workers, and calls them
in the right order. Each worker does one job and reports back.

Nobody hardcoded the sequence. The model has to work out that the guanciale can
render while the pasta boils, and that the egg sauce must never meet a hot pan.
Watching it reason is the demo.

And sometimes it can't. The model is small on purpose, and some orders leave
the expeditor with no plan at all. The plain-Python kitchen owns up to it in so
many words: "Sorry, the kitchen couldn't figure out what to do with that." A
kitchen that fails out loud is part of the show.

Run the four back to back and the differences between them stop being abstract.

## So you compared them. What did you learn?

That is the question, and it is the only reason to build the same thing four
times. Two of the answers were news.

The first is the calls-home column above. Two of the four reach the network
on their own account, and neither asks first. Only one of those calls is
telemetry, and it is crewai's own.

The other is not smolagents' at all. smolagents reaches its model through
LiteLLM, a library underneath it. LiteLLM fetches a price list from GitHub
every time it loads. Nobody had listed that call, and a local model has no
price to look up.

That column is measured, not read. Every hostname each stack looked up while
it cooked was logged, along with the library that asked. Reading the
documentation gives a different answer. langgraph can send traces to
LangSmith, but only once someone turns that on, so in this demo it stays home.

So the lesson is not that frameworks phone home. The dependency tree does, and
from inside any one framework you cannot see which part. That only shows up
with all four side by side, and a log.

The second shows up when you try to install them together. `crewai` declares
`requires-python <3.14`. The other three want 3.14. Nothing warns you until
those two demands are in the same room, and by then you are not comparing
frameworks any more, you are negotiating with a resolver.

Plenty of people are expert in a framework. Far fewer are expert in frameworks,
plural. That gap is most of what this repository is for.

`carbonara` silences both callers before anything starts, and gives every
stack an interpreter of its own. Both are below.

If that made you want to read them rather than run them, they are four files,
one per stack, in `src/carbonara/stacks/`. Each is under 300 lines, and nothing
is shared between them, on purpose. Factor the common parts out and the
comparison goes with it.

## Run it

```bash
carbonara cook-with no-framework --venv
```

`--venv` cooks in a virtual environment of the stack's own, and `--docker` in a
container. Every cook names one. The first run of a stack builds its
environment, then runs the demo. After that it just runs.

Give it a different order, or turn up the chaos:

```bash
carbonara cook-with langgraph --venv --order "carbonara for six, one without cheese"
```

```bash
carbonara cook-with crewai --venv --temperature 0.8
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

That is the good night. Send in an order the kitchen has never heard of, and
the night can end very differently. Both are worth watching.

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

Rather not install the frameworks into a Python of your own? Cook in a container:

```bash
carbonara cook-with crewai --docker
```

Each stack gets an image of its own, and the model stays in Ollama on your
machine, so it runs just as fast. The container sits on a locked network with
no way out. One relay reaches Ollama, and nothing else gets through.

## Requirements

- [Ollama](https://ollama.com) running locally
- Cohere's `tiny-aya` pulled:
  `ollama pull hf.co/CohereLabs/tiny-aya-global-GGUF:Q4_K_M`
- Python 3.14 for `carbonara` itself
- Python 3.12 available for the `crewai` stack
- [Docker](https://www.docker.com), only for `--docker`. That one needs no
  Python 3.12. Tested with Docker Desktop on macOS.

Everything runs on your own machine. No API keys, no cloud, no per-token
billing while you rehearse.

That includes telemetry. Two of the four stacks phone home by default, and
one of them asks mid-demo whether it may upload the run. `carbonara` turns
every switch they honour off before it starts anything, and declines the
tracing prompt so it never interrupts. Nothing here is hidden: `carbonara list`
says so, every cook prints the exact command it runs, and `--telemetry` hands
the frameworks back their own defaults.

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

## More documentation

- [CLI](docs/CLI.md): the command line, word by word
- [Design](docs/DESIGN.md): the interpreter split, the decisions, and the reasons
- [Docker](docs/DOCKER.md): the locked network, the relay, and what it cannot stop
- [Calls home](docs/CALLS-HOME.md): who reaches the network, measured
- [Changelog](CHANGELOG.md): project history and releases

## Use of AI

Code and documentation are written in collaboration with remote and local AI; design
decisions, code review, semantic and auditory review, and final judgement stay human.

---

**East Van AI** · AI for the rest of us! · Vancouver, BC, Canada

[github.com/east-van-ai](https://github.com/east-van-ai) · <east-van-ai@proton.me>

Copyright (c) 2026 Go Nakamaru
