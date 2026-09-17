# Prompting Notes

This repository uses a layered prompt strategy instead of one large prompt.

## Prompt contract overview

| Surface | Input | Output | Key constraint |
| --- | --- | --- | --- |
| Chat | Athlete message plus optional `ATHLETE_ANALYTICS_RESULT` | Plain-text explanation | Use only supplied analytics facts; remain non-medical |
| Recovery | Pre-computed recovery driver analysis | JSON | Do not compute scores or infer new drivers |
| Readiness | Pre-computed readiness driver analysis | JSON | Do not compute scores or infer new drivers |
| Injury Risk | Pre-computed risk driver analysis | JSON | Do not expose risk scores or probabilities |
| Overall State | Prior engine JSON plus ranked overall drivers | JSON | Only compound-flag derivation is allowed |

The prompt system is intentionally narrow: each model gets one job, one expected output shape, and one failure mode.

## Working method

The build process was intentionally iterative:

1. define the user problem and safety boundary first
2. split chat, trend retrieval, and specialist output into separate contracts
3. add tests that prove the contracts from source
4. revise prompts when a test or review exposed ambiguity
5. keep the evaluation text aligned with only verified claims

That sequence matters because it shows Codex being used to steer the implementation, not just generate it.

## Chat prompt

The chat model receives a compact system message that:

- frames the assistant as a wellness and readiness helper
- tells it to use only `ATHLETE_ANALYTICS_RESULT` for factual history
- prevents it from inventing missing values or exposing database internals
- ends with a clear decision-support disclaimer

Acceptance criteria for the chat prompt:

- historical facts must come only from `ATHLETE_ANALYTICS_RESULT`
- missing data must be acknowledged instead of inferred
- the model must stay non-medical
- the response must end with the decision-support disclaimer

Example of a bad chat response:

- invents a missing score or date
- mentions another athlete
- gives diagnosis language

Example of a good chat response:

- summarizes the supplied trend
- states that data is sparse when it is sparse
- stays grounded in the provided payload

Chat review checklist:

- no invented history
- no hidden medical advice
- no mention of another athlete
- clear limitation language when data quality is low
- concise enough to fit a mobile or voice workflow

## Specialist prompts

The specialist models are constrained with:

- JSON-only output requirements
- data-boundary rules
- safety language against diagnosis and raw waveform interpretation
- fixed base-model and tag expectations

Acceptance criteria for specialist prompts:

- output must be valid JSON when required
- the model must not expose raw risk probabilities where forbidden
- the model must not compute scores from raw physiology
- the model must not mention ECG/PPG interpretation beyond explicit prohibition text

Prompt refinement examples:

- recovery/risk outputs were narrowed to data-bound summaries after early drafts over-explained drivers
- the specialist prompts were aligned to fixed tags so tests could verify the model map directly
- the safety language was kept inside the prompt contract so the test suite could lock it in

Specialist review checklist:

- valid JSON only
- output fields match the contract
- no free-form analysis outside the requested scope
- no raw score exposure where prohibited
- phrasing stays within the allowed driver framing

## Iteration notes

The prompt and contract design was refined in small steps:

- first define the problem and safety boundaries
- then commit the prompt contracts
- then add tests that check the contracts directly from source
- then tighten the evaluation report so claims stay within verified evidence

Concrete artifacts that show this iteration:

- [`PROBLEM.md`](PROBLEM.md) records the task scope and what the system is for
- [`ARCHITECTURE.md`](ARCHITECTURE.md) records the request flow and model layout
- [`tests/test_model_contracts.py`](tests/test_model_contracts.py) checks the prompt contracts from source
- [`tests/test_auth_and_schemas.py`](tests/test_auth_and_schemas.py) checks auth and request-boundary behavior
- [`reports/unit-test-report.md`](reports/unit-test-report.md) records the latest verified test run

## Model-specific contract notes

The prompt files are intentionally specialized:

- `Modelfile.chat` is the only surface allowed to receive historical retrieval context.
- `Modelfile.recovery` and `Modelfile.readiness` translate pre-computed drivers for UI cards.
- `Modelfile.risk` must not expose risk scores or probabilities to the athlete.
- `Modelfile.overall` may derive only the documented compound flag and then synthesize the final state.

Those distinctions matter because they keep the prompt layer decomposed instead of mixing retrieval, synthesis, and policy in one place.

## What the prompts are not

- not a claim of clinical accuracy
- not a substitute for authorization
- not a fine-tuning dataset description
- not a guarantee of live runtime performance

The prompt layer is meant to support safe decision support, not to overstate what the system can prove.

## Final prompt quality criteria

This prompt set is strong when all of the following are true:

- every model has a clearly different job
- output shape is stable and testable
- safety constraints are visible in the contract text
- prompt changes are reflected in a source check or unit test
- the reviewer can understand expected behavior without reading code first
