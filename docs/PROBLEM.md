# Problem Statement

RhythmX is a wellness and readiness assistant for athletes. The product is built around a narrow but useful decision-support workflow: take an authenticated athlete question, route it to the right specialized model, and ground any historical analysis in server-side trend data rather than free-form model guesses.

The theme is not generic AI chat. It is athlete decision support for a concrete daily workflow:

- “Has my recovery improved this week?”
- “Is my readiness sliding before a hard training block?”
- “What changed when my injury-risk signal moved?”
- “Compare recovery and sleep over the last 7 days.”

Those are the kinds of questions coaches, athletes, and support staff actually ask when they need a quick, safe read on the last few days of signals.

The core problem is not generic chat. It is safe, athlete-scoped interpretation of recovery, readiness, and injury-risk context with explicit boundaries:

- do not expose other athletes' data
- do not invent missing history
- do not present the assistant as a clinician
- do not let the model infer scores from raw physiology

That scope matters because it keeps the system focused on a real operational need: helping an athlete understand their own wellness signals quickly, while preserving clear safety and privacy boundaries.

In other words, the project is a small, practical bridge between high-volume athlete telemetry and a concise explanation the athlete can act on today.
