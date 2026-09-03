# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

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
