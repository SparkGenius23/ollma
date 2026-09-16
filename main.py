from fastapi import FastAPI, Request, BackgroundTasks
import ollama
from fastapi.responses import StreamingResponse
from ollama import AsyncClient
import json
import logging
import asyncio
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# 1. Configure the Rotating File Handler (1MB max, 3 backups)
file_handler = RotatingFileHandler("app.log", maxBytes=1000000, backupCount=3)

# 2. Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[file_handler, logging.StreamHandler()] # File + Console
)

app = FastAPI()
logger = logging.getLogger(__name__)

# Map engine types to the corresponding custom Ollama model names
MODEL_MAPPING = {
    "chat": "rhythmx-chat:latest",
    "recovery": "rhythmx-recovery:latest",
    "readiness": "rhythmx-readiness:latest",
    "risk": "rhythmx-risk:latest",
    "overall": "rhythmx-overall:latest",
}

OPENAI = {
    'max_tokens': 1024,
    'chat_tokens': 500
}

# Base directory for dataset storage
DATASET_DIR = "../models"

def append_to_runtime_dataset(engine_type: str, user_input: str, full_response: str):
    """
    Appends the interaction to a dynamic daily JSONL dataset file asynchronously.
    Creates files named: runtime_dataset_YYYY-MM-DD.jsonl
    """
    try:
        now = datetime.utcnow()
        date_str = now.strftime("%Y-%m-%d")
        
        # Ensure output directory exists
        os.makedirs(DATASET_DIR, exist_ok=True)
        
        # Dynamically generate filename for current day
        dataset_file = os.path.join(DATASET_DIR, f"runtime_dataset_{date_str}.jsonl")

        record = {
            "timestamp": now.isoformat(),
            "engine": engine_type,
            "instruction": user_input,
            "output": full_response
        }
        with open(dataset_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info(f"Logged query/response pair to {dataset_file} for {engine_type}")
    except Exception as e:
        logger.error(f"Failed to record runtime dataset entry: {str(e)}")


async def stream_content(messages, model_name: str, engine_type: str = "", background_tasks: BackgroundTasks = None):
    """
    Fixed async generator for true non-blocking streaming + runtime dataset recording.
    """
    client = AsyncClient()
    accumulated_response = []
    user_input = messages[0].get("content", "") if messages else ""

    async for chunk in await client.chat(
        model=model_name,
        messages=messages,
        think=True,
        stream=True,
        options={
            'num_predict': OPENAI['chat_tokens'] if engine_type == 'chat' else OPENAI['max_tokens'],
            "top_k": 1,
            "repeat_penalty": 1.0,
            'keep_alive': '5m',
            'reasoning_effort': 'low',
            'max_thinking_tokens': 1024,
        }
    ):
        content = chunk.get('message', {}).get('content', '')
        
        if content:
            accumulated_response.append(content)
            yield content  # Yield immediately to front-end stream

    # After full response completes, log to dataset via background task
    full_response_str = "".join(accumulated_response).strip()
    if background_tasks and full_response_str:
        background_tasks.add_task(
            append_to_runtime_dataset, 
            engine_type, 
            user_input, 
            full_response_str
        )


@app.post("/chat/")
async def get_chat_stream(request: Request, background_tasks: BackgroundTasks):
    json_data = await request.json()
    requested_content = json_data.get("content", "")
    
    messages = [
        {"role": "user", "content": requested_content}
    ]

    logger.info("Chat Stream log initiated")
    
    return StreamingResponse(
        stream_content(messages, model_name=MODEL_MAPPING["chat"], engine_type="chat", background_tasks=background_tasks), 
        media_type="text/plain"
    )

@app.post("/intelligence/{engine_type}")
async def get_intelligence_stream(request: Request, engine_type: str, background_tasks: BackgroundTasks):
    json_data = await request.json()
    requested_content = json_data.get("content", "")

    # Clean the path string to guarantee exact dictionary matching
    clean_engine_key = engine_type.strip().lower()

    # Look up target model
    model_name = MODEL_MAPPING.get(clean_engine_key, MODEL_MAPPING["chat"])

    # LOG THIS WARN TO CONFIRM IF FALLBACK OCCURS
    if clean_engine_key not in MODEL_MAPPING:
        logger.warning(f"Engine key '{clean_engine_key}' not found in MODEL_MAPPING! Falling back to {model_name}")

    messages = [
        {"role": "user", "content": requested_content}
    ]

    logger.info(f"LLM Stream log initiated: {clean_engine_key} using model: {model_name}")
    
    return StreamingResponse(
        stream_content(messages, model_name=model_name, engine_type=clean_engine_key, background_tasks=background_tasks), 
        media_type="application/json"
    )