# Unit Test Report

## Result

| Status | Tests run | Passed | Failed | Errors | Duration |
| --- | ---: | ---: | ---: | ---: | ---: |
| PASS | 34 | 34 | 0 | 0 | 0.039s |

## Execution

```bash
python -m unittest discover -s tests -v
```

Run date: 2026-09-17 (America/Halifax)

## Evidence boundary

This report records deterministic unit tests only. Request-routing tests use fakes and stubs for runtime services, while prompt-contract tests inspect local source files. This pass does not establish a live Ollama response, database connectivity, token/latency performance, authentication, or clinical injury-prediction quality. See [`EVALUATION.md`](../EVALUATION.md) for the repeatable runtime, prompt, and benchmark evidence required before making those claims.

## Coverage by test module

| Module | Tests | Coverage |
| --- | ---: | --- |
| `tests.test_intent` | 3 | Wellness trend parsing, metric-comparison parsing, inclusive date ranges |
| `tests.test_auth_and_schemas` | 12 | JWT configuration, athlete-ID constraints, request-schema boundaries, and bearer-token challenge handling |
| `tests.test_main` | 9 | Athlete identity, routing, history bounds, database availability, health endpoints, and timezone validation |
| `tests.test_model_contracts` | 6 | Five-model inventory, runtime model-tag mapping, approved base model, specialist JSON/data boundaries, and chat/raw-signal safety contracts |
| `tests.test_trends` | 4 | Supporting wellness metrics, previous-period comparison, and invalid-metric rejection |

## Notes

- Request-routing tests use fakes and stubs for Postgres, Ollama, and optional runtime packages.
- The repository now includes a minimal local compatibility layer so schema assertions run in this container instead of skipping.
- Security-oriented tests now cover the bearer challenge header, valid-token success, and nondisclosive health endpoints.
- Prompt-contract tests are static checks of the local Modelfiles and `MODEL_MAPPING`.
- No external database or model service was contacted.
