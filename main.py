from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import asyncpg
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from ollama import AsyncClient

from app.intent import IntentType, date_range_for, parse_intent
from app.trends import TrendService

file_handler = RotatingFileHandler("app.log", maxBytes=1_000_000, backupCount=3)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[file_handler, logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
app = FastAPI(title="RhythmX Intelligence API")

MODEL_MAPPING = {
    "chat": "rhythmx-chat:latest",
    "recovery": "rhythmx-recovery:latest",
    "readiness": "rhythmx-readiness:latest",
    "risk": "rhythmx-risk:latest",
    "overall": "rhythmx-overall:latest",
}

# Load the deployment-local .env file without overriding systemd environment variables.
load_dotenv(Path(__file__).with_name(".env"))
DATABASE_URL = os.getenv("DATABASE_URL")
# Output limits live in each Modelfile. Thinking remains an API option because
# Ollama does not support max_thinking_tokens as a Modelfile parameter.
CHAT_MAX_THINKING_TOKENS = 384
ENGINE_MAX_THINKING_TOKENS = 256
DATASET_DIR = Path(__file__).with_name("models")

ANALYTICS_SYSTEM_MESSAGE = """
You are the RhythmX Wellness & Readiness Assistant.
Use only ATHLETE_ANALYTICS_RESULT for personal dates, scores, trends, and comparisons.
Do not calculate missing values, invent history, expose database internals, diagnose, or give medical advice.
When data quality is limited, state that clearly. For historical requests, use concise bullets or a table.
End with: Decision-support, not medical advice.
""".strip()


@app.on_event("startup")
async def startup() -> None:
    app.state.db_pool = None
    if DATABASE_URL:
        app.state.db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        logger.info("TimescaleDB pool initialized")
    else:
        logger.warning("DATABASE_URL is not configured; score-history chat is disabled")


@app.on_event("shutdown")
async def shutdown() -> None:
    pool = getattr(app.state, "db_pool", None)
    if pool:
        await pool.close()


@app.get("/health/db")
async def database_health():
    """Read-only database readiness probe; no credentials or health data are returned."""
    pool = getattr(app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )
    try:
        await pool.fetchval("SELECT 1")
    except asyncpg.PostgresError as exc:
        logger.error("Database readiness check failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc
    return {"status": "ok", "database": "connected"}


def append_to_runtime_dataset(engine_type: str, user_input: str, full_response: str) -> None:
    """Append a completed model interaction to the daily JSONL retraining dataset."""
    try:
        DATASET_DIR.mkdir(parents=True, exist_ok=True)
        dataset_file = DATASET_DIR / f"runtime_dataset_{datetime.utcnow():%Y-%m-%d}.jsonl"
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "engine": engine_type,
            "instruction": user_input,
            "output": full_response,
        }
        with dataset_file.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info("Logged completed %s interaction to runtime dataset", engine_type)
    except OSError as exc:
        logger.error("Failed to record runtime dataset: %s", type(exc).__name__)


async def stream_content(
    messages: list[dict], model_name: str, engine_type: str = "", background_tasks: BackgroundTasks | None = None
):
    """Stream an Ollama answer and persist the completed request/response asynchronously."""
    client = AsyncClient()
    accumulated_response: list[str] = []
    user_input = "\n\n".join(
        str(message.get("content", "")) for message in messages if message.get("role") == "user"
    )
    options = {
        "top_k": 1,
        "repeat_penalty": 1.0,
        "keep_alive": "5m",
        "reasoning_effort": "low",
        "max_thinking_tokens": CHAT_MAX_THINKING_TOKENS if engine_type == "chat" else ENGINE_MAX_THINKING_TOKENS,
    }
    async for chunk in await client.chat(
        model=model_name, messages=messages, think=True, stream=True, options=options
    ):
        content = chunk.get("message", {}).get("content", "")
        if content:
            accumulated_response.append(content)
            yield content
    full_response = "".join(accumulated_response).strip()
    if background_tasks and full_response:
        background_tasks.add_task(append_to_runtime_dataset, engine_type, user_input, full_response)


def _athlete_id_from_body(value: object) -> int:
    """Parse an explicit Django auth.User primary key supplied by the request body."""
    try:
        user_id = int(value)  # Accept JSON number or numeric string.
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="athlete_id is required") from exc
    if user_id <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid athlete_id")
    return user_id


def _athlete_today(timezone_name: str):
    try:
        return datetime.now(ZoneInfo(timezone_name)).date()
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid timezone") from exc


async def _chat_payload(request: Request) -> tuple[str, str]:
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="JSON object is required")
    athlete_id = _athlete_id_from_body(body.get("athlete_id"))
    message = body.get("message") or body.get("content")
    if not isinstance(message, str) or not message.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="message is required")
    message = message.strip()
    intent = parse_intent(message)
    date_range = date_range_for(intent, _athlete_today(body.get("timezone") or "UTC"))

    if intent.intent in {IntentType.TREND, IntentType.PERIOD_COMPARISON, IntentType.METRIC_COMPARISON}:
        pool = getattr(app.state, "db_pool", None)
        if pool is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Score-history service is not configured",
            )
        assert date_range is not None
        analytics = await TrendService(pool).build_payload(
            athlete_id, intent, *date_range
        )
        return message, json.dumps(analytics, separators=(",", ":"))
    return message, ""


@app.post("/chat/")
async def get_chat_stream(request: Request, background_tasks: BackgroundTasks):
    """
    Chat endpoint using the body-provided athlete_id. Retrieval completes before streaming.
    """
    message, analytics_context = await _chat_payload(request)
    messages = [
        {"role": "system", "content": ANALYTICS_SYSTEM_MESSAGE},
        {"role": "user", "content": message},
    ]
    if analytics_context:
        messages.append({"role": "user", "content": f"ATHLETE_ANALYTICS_RESULT:\n{analytics_context}"})
    logger.info("Chat request accepted; analytics=%s", bool(analytics_context))
    return StreamingResponse(
        stream_content(
            messages, model_name=MODEL_MAPPING["chat"], engine_type="chat", background_tasks=background_tasks
        ),
        media_type="text/plain",
        background=background_tasks,
    )


@app.post("/intelligence/{engine_type}")
async def get_intelligence_stream(request: Request, engine_type: str, background_tasks: BackgroundTasks):
    """Existing current-day intelligence endpoint retained for engine callers."""
    body = await request.json()
    clean_engine_key = engine_type.strip().lower()
    model_name = MODEL_MAPPING.get(clean_engine_key)
    if model_name is None or clean_engine_key == "chat":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown intelligence engine")
    return StreamingResponse(
        stream_content(
            [{"role": "user", "content": body.get("content", "")}],
            model_name,
            clean_engine_key,
            background_tasks,
        ),
        media_type="text/plain",
        background=background_tasks,
    )
