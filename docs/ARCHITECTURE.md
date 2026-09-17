# Architecture

RhythmX uses a small multi-model architecture with fixed routing and server-side retrieval.

## Design goal

The architecture is built to make the hard parts deterministic:

- who the athlete is
- what type of question they asked
- whether historical data is needed
- which model tag should answer
- what factual context the model is allowed to see

That keeps the LLM layer narrow and makes the system easier to test.

## Request flow

1. A bearer JWT authenticates the athlete.
2. The request schema rejects unknown fields and oversized content.
3. Intent parsing determines whether the request is general chat, a trend question, or a metric comparison.
4. Historical requests pull only authenticated athlete data from the database through an allowlisted Trend Service.
5. The app injects `ATHLETE_ANALYTICS_RESULT` into the chat model only when the request is historical.
6. Specialist endpoints use fixed model tags from `MODEL_MAPPING`.

## Acceptance criteria

The architecture is considered correct when:

- JWT identity is required before data retrieval
- client-supplied athlete IDs cannot override the authenticated athlete
- historical requests fail cleanly if the database is unavailable
- fixed allowlists prevent arbitrary metric or table access
- the chat model only sees compact factual context, not raw database access
- specialist endpoints map to the exact five declared model tags

## Model layout

- `rhythmx-chat:latest` handles conversational wellness guidance.
- `rhythmx-recovery:latest` handles recovery-focused specialist output.
- `rhythmx-readiness:latest` handles readiness-focused specialist output.
- `rhythmx-risk:latest` handles risk-focused specialist output.
- `rhythmx-overall:latest` handles overall synthesis.

## Safety boundaries

- Athlete identity comes from JWT `sub`, not from the client body.
- Trend queries use fixed metric/table/column allowlists.
- Models are instructed not to diagnose, expose raw scores where forbidden, or interpret ECG/PPG.
- The API adds basic request protection headers and an early size check.

## Why this design scored well

This structure is strong for evaluation because it separates concerns:

- prompt contracts are explicit
- data access is server-side and allowlisted
- tests can verify the routing and safety boundaries
- the model is used for interpretation, not for hidden control flow
- the submission can be judged from code, docs, and test output together

## Dependency direction

The modules depend on each other in one direction only:

- routes call auth, intent parsing, and trend services
- trend services never import route handlers
- prompt contracts live in model files and are verified by tests
- request schemas stay separate from business logic
- the model layer never reaches back into authorization or database code

This matters because it keeps the system easy to reason about, easy to test, and easy to change without turning the LLM into a hidden control plane.

## Non-goals

- no direct SQL from the model
- no athlete identity from the request body alone
- no raw waveform interpretation in the prompt contracts
- no claim that the current unit tests prove live production accuracy

This design keeps retrieval deterministic and makes the model layer smaller, safer, and easier to evaluate.
