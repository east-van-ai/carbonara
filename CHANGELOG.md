# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.2.5] - 2026-10-20

### Changed

- `--docker` cooks behind a locked network, with a relay to Ollama as the only way
  out, not on Docker's default network. `--telemetry` opens it. A locked cook prints
  the relay's commands around the stack's.

### Added

- `docs/DOCKER.md` holds Docker mode, the lock, and a probe showing the relay passes
  Ollama's whole API.

## [0.2.4] - 2026-10-20

### Added

- `--docker` on `prep` and `cook-with` builds a stack's image and cooks in a
  container, with Ollama on the host. `carbonara list` shows each image beside its
  venv.
- Every cook prints the command that runs the stack, ready to paste into a shell.
  An image build prints its `docker build` line.

### Fixed

- The `--telemetry` notice no longer lands after the stack's output when stdout is
  a pipe.

## [0.2.3] - 2026-10-15

### Added

- `docs/CALLS-HOME.md` records which stacks reach the network, which library makes
  each call, and the switch that stops it, all measured, with the way to measure it
  again.
- The README links the other documents from a More documentation section.

### Fixed

- `carbonara list`, the banner, and the README count two stacks that call home,
  crewai and smolagents, as measured. langgraph calls home only once LangSmith
  tracing is on.

## [0.2.2] - 2026-10-15

### Changed

- The pinned requirements are refreshed: crewai 1.15.28, langgraph 1.2.15, and
  LiteLLM 1.105.1 under smolagents. An existing install picks them up with
  `carbonara prep STACK`.

### Fixed

- smolagents no longer fetches LiteLLM's price list from GitHub on every run.
  `LITELLM_LOCAL_MODEL_COST_MAP` joins the telemetry switches.
- langgraph's pinned set no longer carries the `black` formatter.
- crewai and smolagents follow `OLLAMA_HOST`. Every stack now reads its Ollama URL
  from `CARBONARA_OLLAMA_URL`.

## [0.2.1] - 2026-09-15

### Added

- `carbonara version` prints the installed version, the same line as
  `--version`.

### Changed

- The banner no longer lists `--version`.
- `DESIGN.md` moves to `docs/DESIGN.md`, and its command-surface half becomes
  `docs/CLI.md`.

## [0.2.0] - 2026-09-03

### Changed

- The default model is Cohere's `tiny-aya`, pulled from HuggingFace as
  `hf.co/CohereLabs/tiny-aya-global-GGUF:Q4_K_M`.

### Fixed

- The expeditor's plan parser in `no-framework` and `langgraph` reads `CALL`
  lines through markdown, so a numbered or bolded plan is no longer dropped.

## [0.1.0] - 2026-08-27

### Added

- `carbonara cook-with STACK` cooks the demo with one of four agent stacks, in
  an environment of its own. The first cook with a stack builds it.
- `carbonara prep STACK` builds that environment on its own, pinned by default
  and from the unpinned requirements with `--latest`.
- `carbonara list` reports every stack, the interpreter it wants, whether its
  environment is built, which of them calls home, and Ollama's state.
- `--order`, `--model`, `--temperature`, and `--stream-delay` reach a stack as
  `CARBONARA_*` environment variables, so the demo can be steered without
  editing the script.
- Telemetry is off for every stack, and `--telemetry` hands the frameworks back
  their own defaults. Three of the four reach the network unasked.
- crewai's tracing prompt is declined and `CREWAI_STORAGE_DIR` pinned, since no
  environment variable can turn that tracing off.
- The four implementations are vendored from their own repos and ship as
  package data, never imported.
