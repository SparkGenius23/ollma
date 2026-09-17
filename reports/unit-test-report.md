# Unit Test Report

## Result

| Status | Tests run | Passed | Failed | Errors | Duration |
| --- | ---: | ---: | ---: | ---: | ---: |
| PASS | 10 | 10 | 0 | 0 | 0.044s |

## Execution

```bash
python -m unittest discover -v
```

Run date: 2026-09-17 (America/Halifax)

## Coverage by test module

| Module | Tests | Coverage |
| --- | ---: | --- |
| `tests.test_intent` | 3 | Wellness trend parsing, metric-comparison parsing, inclusive date ranges |
| `tests.test_main` | 5 | Athlete ID validation, general chat routing, trend analytics routing, unavailable database handling |
| `tests.test_trends` | 2 | Supporting wellness metrics in trend and metric-comparison payloads |

## Notes

- Tests use fakes and stubs for Postgres, Ollama, and optional runtime packages.
- No external database or model service was contacted.
