# RhythmX Intelligence API

RhythmX is a Model-as-a-Service (MaaS) athlete decision-support gateway. It routes authenticated requests to independently versioned Ollama models, keeps historical retrieval server-side, and constrains each model to a narrow task-specific prompt contract.

The project is centered on one theme: helping athletes understand recovery, readiness, and injury-risk context quickly enough to change training decisions, without handing the model direct control over identity, retrieval, or scoring.

The service provides specialised endpoints for recovery, readiness, injury risk, overall state, and conversational athlete insights. Historical chat requests are enriched with a read-only TimescaleDB/PostgreSQL query before being passed to the chat model.

> Decision-support only. This application is not a medical device and must not be used for diagnosis or treatment.

## Architecture

```text
Client
  |
  v
FastAPI gateway (main.py)
  |-- /intelligence/recovery  --> rhythmx-recovery
  |-- /intelligence/readiness --> rhythmx-readiness
  |-- /intelligence/risk      --> rhythmx-risk
  |-- /intelligence/overall   --> rhythmx-overall
  `-- /chat/                  --> intent parsing --> optional TimescaleDB retrieval --> rhythmx-chat
                                                                          |
                                                                          `--> streamed plain-text response
```

Each model is declared in `models/Modelfile.*` and is designed for one responsibility:

| Model | Purpose |
| --- | --- |
| `rhythmx-chat` | Non-medical athlete-facing chat and historical trend synthesis |
| `rhythmx-recovery` | Explains pre-computed recovery drivers |
| `rhythmx-readiness` | Explains pre-computed readiness drivers |
| `rhythmx-risk` | Explains pre-computed injury-risk drivers without exposing risk scores |
| `rhythmx-overall` | Synthesises the domain-engine outputs into an overall-state result |

The application does not calculate wellness scores or interpret raw ECG waveforms. Upstream services supply validated, pre-computed context and ECG-derived features; the MaaS models translate or synthesise that context under their respective prompt contracts.

### Layering

The codebase is intentionally split into a few small, testable boundaries:

| Layer | Responsibility |
| --- | --- |
| `app/auth.py` | JWT authentication and athlete identity checks |
| `app/intent.py` | Deterministic intent and date-range parsing |
| `app/schemas.py` | Size-bounded request contracts |
| `app/trends.py` | Allowlisted historical retrieval and summary shaping |
| `main.py` | API orchestration, response streaming, and health middleware |
| `models/Modelfile.*` | Prompt contracts for each specialized model |

That separation is the main design choice behind the project: the LLM is used for interpretation, not for routing, authorization, or direct data access.

### Trend Service: token-aware historical retrieval

`TrendService` is the data boundary for historical chat. Before the chat model is invoked, the gateway's deterministic intent parser identifies the requested metric, date range, and comparison type from a supported phrase. `TrendService` then performs read-only, parameterised queries against a fixed server-side allowlist, selects the latest record for each day, and returns structured daily values, summaries, data-quality metadata, and only the aligned supporting signals required for the question.

This architecture reduces model-context tokens compared with sending raw wearable events, entire database rows, or an athlete's unfiltered history to the LLM. The database performs retrieval and numerical aggregation; the model receives a compact `ATHLETE_ANALYTICS_RESULT` payload and focuses on explanation. Token savings vary with the athlete's history and requested period, so they should be measured in production rather than assumed.

### Design invariants

- The client never chooses the authenticated athlete.
- Historical queries never use free-form metric, table, or column names.
- The chat model only sees compact facts after retrieval succeeds.
- Specialist endpoints use fixed tags and fixed contracts.
- Safety and nondisclosure are enforced both in code and in prompts.

### Theme fit

The clearest evidence that the project matches its theme is the chat workflow:

1. an athlete asks about recovery, readiness, sleep, or injury risk
2. the gateway parses the intent deterministically
3. the server fetches only the athlete's own historical signals
4. the model receives a compact factual payload
5. the response stays non-medical and decision-focused

That makes the system suitable for athlete-facing workflow support instead of generic question answering.

## Injury-prediction data requirements

Reliable one-month-ahead injury-risk prediction depends on consistent, longitudinal athlete data. The upstream scoring pipeline should provide daily records, with sufficient history and coverage, for relevant signals such as:

- ECG-derived cardiovascular features (for example HRV and resting heart rate), rather than raw ECG waveforms
- Sleep duration, quality, and regularity
- Nutrition and hydration
- Training load and workload changes
- Recovery, fatigue, stress, soreness, ARI, SpO2, and athlete-reported wellness data
- Return-to-play, illness, and other relevant training-context flags

Missing, sparse, inconsistent, or low-quality data reduces confidence and can prevent a meaningful forward-looking prediction. The API carries available-data and confidence information into historical analyses; upstream services remain responsible for feature extraction, data validation, risk scoring, and prediction-horizon calibration.

## Prerequisites

- Python 3.10+ (3.11+ recommended)
- An accessible [Ollama](https://ollama.com/) service with the base model available
- PostgreSQL/TimescaleDB only when historical trend and comparison chat is required

## Local setup

Create and activate a virtual environment, then install the API dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create the MaaS model instances. The included Modelfiles use `gpt-oss:20b`; pull or otherwise make that base model available first, then create the five endpoint models:

```bash
ollama pull gpt-oss:20b
ollama create rhythmx-chat -f models/Modelfile.chat
ollama create rhythmx-recovery -f models/Modelfile.recovery
ollama create rhythmx-readiness -f models/Modelfile.readiness
ollama create rhythmx-risk -f models/Modelfile.risk
ollama create rhythmx-overall -f models/Modelfile.overall
```

Copy `.env.example` to `.env` next to `main.py`, then configure the optional database connection:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
CHAT_MAX_OUTPUT_TOKENS=300
CHAT_MAX_THINKING_TOKENS=512
```

`DATABASE_URL` is optional. Without it, normal chat and all intelligence endpoints continue to work, while history-dependent chat requests return `503`.

Run the API:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

## Deploying on AWS EC2

The recommended production topology keeps Ollama private and exposes only the FastAPI gateway through HTTPS. For a simple deployment, run FastAPI and Ollama on the same GPU EC2 instance; the gateway then talks to Ollama over `127.0.0.1:11434`.

```text
Internet --> HTTPS ALB or NGINX --> FastAPI :8000 --> Ollama :11434 (private)
                                      |                 |
                                      `--> PostgreSQL / TimescaleDB
```

### 1. Provision the host

Launch Ubuntu 22.04 LTS on a GPU-backed EC2 instance with a current AWS Deep Learning, NVIDIA-enabled, or otherwise GPU-ready AMI.

| Workload | Suggested instance | Rationale |
| --- | --- | --- |
| Development / standard quantized inference | `g6.xlarge` (NVIDIA L4, 24 GB VRAM) | Practical default for 4-bit `gpt-oss:20b` with useful KV-cache headroom |
| Longer contexts or more concurrency | `g6e.xlarge` (NVIDIA L40S, 48 GB VRAM) | More VRAM for larger context windows and parallel requests |
| Cost-sensitive experiments | GPU Spot capacity | Suitable only when the application can tolerate interruption and restart |

Attach at least 50 GB of gp3 EBS storage for Ubuntu, the model files, logs, and runtime datasets; increase the volume for retained datasets or multiple model versions. Confirm the exact instance availability and current AWS pricing in the target Region before launch.

Configure security groups with least privilege:

- Allow SSH (`22`) only from an administrator CIDR or use AWS Systems Manager Session Manager.
- Do **not** expose Ollama (`11434`) publicly. When FastAPI and Ollama share a host, no inbound rule for `11434` is needed.
- If using an Application Load Balancer (ALB), expose `443` at the ALB, and allow the EC2 application's port (`8000`) only from the ALB security group.
- If FastAPI calls Ollama on a separate EC2 host, allow `11434` only from the FastAPI security group within the VPC.

Connect to the instance and verify GPU availability. GPU-ready AWS images usually have a working driver; install a driver only if this check fails.

```bash
ssh -i /path/to/key.pem ubuntu@EC2_PUBLIC_DNS
nvidia-smi

# Only when the driver is missing on Ubuntu:
sudo apt update
sudo apt install -y nvidia-driver-550
sudo reboot
```

### 2. Install and verify Ollama

After reconnecting, install Ollama and confirm that the service and GPU are ready:

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl status ollama --no-pager
ollama pull gpt-oss:20b
ollama run gpt-oss:20b "Reply with: Ollama is ready."
```

Create the five model endpoints from this repository:

```bash
cd /opt/rhythmx
ollama create rhythmx-chat -f models/Modelfile.chat
ollama create rhythmx-recovery -f models/Modelfile.recovery
ollama create rhythmx-readiness -f models/Modelfile.readiness
ollama create rhythmx-risk -f models/Modelfile.risk
ollama create rhythmx-overall -f models/Modelfile.overall
ollama list
```

Keep Ollama on its default loopback binding when it shares the instance with the API. If Ollama must serve another private host, configure a systemd override and restrict port `11434` to the calling security group:

```bash
sudo systemctl edit ollama
```

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

Then reload and restart the service:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

Never use this setting with a public `11434` security-group rule.

### 3. Deploy the API as a service

Copy or clone this repository to `/opt/rhythmx`, then install its dependencies:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv
sudo mkdir -p /opt/rhythmx /etc/rhythmx
sudo chown ubuntu:ubuntu /opt/rhythmx

# Clone your deployed repository revision into /opt/rhythmx, then:
cd /opt/rhythmx
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

Create the environment file. `DATABASE_URL` is required for trend and comparison chat; all other model endpoints work without it.

```bash
sudo tee /etc/rhythmx/rhythmx.env >/dev/null <<'EOF'
DATABASE_URL=postgresql://USER:PASSWORD@DATABASE_HOST:5432/DATABASE_NAME
OLLAMA_HOST=http://127.0.0.1:11434
CHAT_MAX_OUTPUT_TOKENS=300
CHAT_MAX_THINKING_TOKENS=512
EOF
sudo chmod 640 /etc/rhythmx/rhythmx.env
sudo chown root:ubuntu /etc/rhythmx/rhythmx.env
```

Create `/etc/systemd/system/rhythmx.service`:

```ini
[Unit]
Description=RhythmX Intelligence API
After=network-online.target ollama.service
Wants=network-online.target
Requires=ollama.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/rhythmx
EnvironmentFile=/etc/rhythmx/rhythmx.env
ExecStart=/opt/rhythmx/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and check the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rhythmx
sudo systemctl status rhythmx --no-pager
curl http://127.0.0.1:8000/openapi.json
```

The gateway runs on loopback in this configuration. Put NGINX on the same host or an HTTPS ALB in front of it. If an ALB connects directly to Uvicorn, bind Uvicorn to `0.0.0.0` instead and allow port `8000` only from the ALB security group. Use `/openapi.json` as an infrastructure health check when the database is optional; `/health/db` intentionally reports `503` without a configured, reachable database.

### 4. Production hardening and operations

- Terminate TLS at an ALB or NGINX, authenticate callers at the gateway, and keep model traffic inside the VPC.
- Store `DATABASE_URL` in AWS Secrets Manager or SSM Parameter Store for production rather than committing it or leaving it in a user-readable file.
- Review `journalctl -u ollama` and `journalctl -u rhythmx` during deployment and send logs and GPU metrics to CloudWatch.
- Start with default Ollama concurrency. On a tested, high-VRAM host, a systemd override can set `OLLAMA_NUM_PARALLEL=4`; monitor `nvidia-smi`, latency, and out-of-memory errors before raising it further.
- Keeping models resident with `OLLAMA_KEEP_ALIVE=-1` removes cold-start delay but increases idle GPU cost. Use it only for an always-on workload; otherwise retain the application's five-minute request keep-alive.
- Use EBS snapshots for recoverable model and configuration state. For development environments, schedule CloudWatch-driven shutdown after sustained idle GPU use; use Spot capacity only for interruptible workloads.

## API

### Health check

```bash
curl http://localhost:8000/health/db
```

This endpoint returns `200` only when the database pool can execute a read-only probe. It returns `503` if the database is absent or unavailable.

### Intelligence endpoints

Send pre-computed, domain-specific context to one of the specialist engines. Responses are streamed as `text/plain`.

```bash
curl -N -X POST http://localhost:8000/intelligence/recovery \
  -H 'Content-Type: application/json' \
  -d '{"content":"=== RECOVERY (normal) ===\nRecovery Score: 76\nSleep Score: 80"}'
```

Allowed engine paths are:

- `/intelligence/recovery`
- `/intelligence/readiness`
- `/intelligence/risk`
- `/intelligence/overall`

The `chat` model is intentionally exposed only through `/chat/`. Unknown engine names return `404`.

### Athlete chat

`/chat/` accepts an explicit Django `auth.User` primary key and a message. `timezone` is optional and defaults to `UTC`.

```bash
curl -N -X POST http://localhost:8000/chat/ \
  -H 'Content-Type: application/json' \
  -d '{
    "athlete_id": 42,
    "message": "Show my recovery trend over the last 7 days",
    "timezone": "America/Halifax"
  }'
```

Supported historical intent includes trends, current-vs-prior-period comparisons, and comparisons between supported metrics. The gateway maps recognised phrases to a server-side metric allowlist before querying the database; raw SQL identifiers never come from the request.

See [curl samples](docs/curl-samples.md) for more request examples.

## Data integration

For historical chat, the API reads the latest daily record per athlete from these existing tables:

- `ts_model_output_recovery_score`
- `ts_model_output_readiness_index`
- `ts_model_output_risk_score`

It supports recovery, readiness, injury risk, HRV, RHR, sleep, nutrition, hydration, ARI, SpO2, stress, soreness, and fatigue. Trend payloads include daily values, pre-computed summaries, data-quality metadata, and aligned recovery inputs for context. The chat model is instructed to rely only on the assembled, token-scoped `ATHLETE_ANALYTICS_RESULT` for personal historical claims.

Completed model interactions are appended to `models/runtime_dataset_YYYY-MM-DD.jsonl` for later retraining analysis. Treat these files as sensitive athlete data and keep them out of source control and unapproved storage.

## Configuration and operations

- The gateway uses the Ollama Python client's default connection settings; point the client at the intended Ollama instance through its supported environment configuration.
- Chat output and thinking budgets are controlled by `CHAT_MAX_OUTPUT_TOKENS` and `CHAT_MAX_THINKING_TOKENS`.
- Model calls request a five-minute keep-alive to reduce cold-start latency.
- Application logs are written to stdout and a rotating `app.log` file (1 MB per file, three backups).
- Keep model names in `MODEL_MAPPING` in sync with the `ollama create` commands and deployed model tags.

## Tests

Run the unit-test suite with the standard library test runner:

```bash
python -m unittest discover -s tests -v
```

The tests cover intent parsing, date-range handling, trend payload construction, and API request routing. They provide lightweight stubs for optional runtime packages where necessary.

## Repository layout

```text
main.py              FastAPI MaaS gateway and streaming integration
app/intent.py        Safe historical-chat intent parsing
app/trends.py        Read-only trend retrieval and summarisation
models/Modelfile.*   Ollama model definitions and prompt contracts
schema/model.py      Django/Timescale model schema reference
tests/               Unit tests
docs/                Architecture notes and request samples
```

For the broader prompt-microservices rationale, see [Prompt Microservices Architecture](docs/Prompt%20Microservices%20Architecture.md).
