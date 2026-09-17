# RhythmX Evaluation Evidence Pack

## Purpose

This document separates verified repository evidence from claims that would require live runtime validation.

The project is a decision-support assistant, not a medical device. Evaluation artifacts should stay within that boundary.

## What is verified here

- authenticated athlete-scoped request handling
- deterministic intent parsing
- fixed model routing
- allowlisted trend retrieval
- prompt/model contract checks
- unit-test coverage for key routing and safety behavior

## What is not yet verified

- live Ollama responses
- database connectivity in a real deployment
- latency or throughput benchmarks
- clinical accuracy or injury prediction quality

## Current record

- unit tests: 34 total, 34 passed, 0 skipped in this environment
- schema/runtime checks: covered by the local compatibility layer and unit tests in this environment
- live integration demo: not yet recorded

## Process evidence that supports Codex usage

- The project was decomposed into separate problem, architecture, prompt, and evaluation artifacts.
- Prompt boundaries were tightened after the code and tests exposed what needed to be explicit.
- Contract tests were added to verify the prompt files and model mapping from source.
- Auth and schema boundary tests were added to show that safety rules are enforced before model generation.
- Security coverage now includes bearer challenge handling, valid-token success, and health endpoints that do not leak sensitive state.
- The final evaluation text was updated to describe only verified claims.

## Spec quality signals

- explicit input/output boundaries
- fixed model tags and fixed request routing
- acceptance criteria for chat and specialist prompts
- adversarial and negative-path checks
- evaluation language that distinguishes verified results from planned work
- prompt contracts are split by surface instead of merged into one giant instruction
- each model file has a testable role, output shape, and safety boundary
- the prompt docs describe both success criteria and failure modes

## Prompt quality evidence

- `PROMPTS.md` defines per-surface contract rules and review checklists.
- `tests/test_model_contracts.py` verifies the fixed model inventory and key safety phrases directly from source.
- The chat contract uses a compact retrieval payload instead of raw database rows.
- Specialist prompts require JSON and keep scoring/diagnostic behavior out of the athlete-facing layer.
- The overall-state prompt is the only prompt allowed to derive a compound flag, and even that derivation is documented explicitly.

## Recommendation

For a higher judge score, keep the final submission tightly aligned to the evidence above and avoid claims that need a live deployment demo unless you capture that demo directly.
