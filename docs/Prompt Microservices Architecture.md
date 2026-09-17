# Prompt Microservices Architecture

RhythmX uses a prompt-microservice style design: one authenticated chat orchestrator, one deterministic trend service, and multiple fixed specialist model endpoints.

The point of this structure is to keep the model layer narrow and auditable:

- route by intent before generation
- fetch historical data server-side
- inject only a compact analytics payload
- keep specialist endpoints on fixed model tags
- keep safety and privacy rules in the prompt contract

That lets the system behave more like a conventional service architecture and less like a single oversized prompt.
