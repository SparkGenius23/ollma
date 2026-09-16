from fastapi import FastAPI, Request
from prompt import prompts
import ollama
from fastapi.responses import StreamingResponse
from ollama import AsyncClient # Import the AsyncClient
import json
import logging
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

OPENAI = {
    'MODEL': "gpt-oss:20b",
    'max_tokens': 2048,
    'chat_tokens': 250
}

async def stream_content(messages, engine_type = ""):
    """
    Fixed async generator for true non-blocking streaming.
    """
    client = AsyncClient() # Create the async client instance

    # We await the chat call, but iterate over it as an async generator
    async for chunk in await client.chat(
        model=OPENAI['MODEL'],
        messages=messages,
        think=True,
        stream=True, # Critical: must be True to get chunks
        options={
            'num_predict': OPENAI['max_tokens'],
            'temperature': 0.2,
            "top_p": 1.0,
            "top_k": 1,
            "repeat_penalty": 1.0,
            
            # Force the model to use minimal reasoning effort
            'reasoning_effort': 'low',
        
            # Strictly limit how many tokens it can waste on "thinking"
            'max_thinking_tokens': 1024,
            # Prevent the model from rambling endlessly
            #'num_predict': 2048,
        }
    ):
        #logstr = f"Intelligence LLM {engine_type}" if engine_type else "Chat"
        # Extract content from the chunk
        # Ollama's async response structure: chunk['message']['content']
        content = chunk.get('message', {}).get('content', '')
        
        # Handle 'thinking' field if using models like DeepSeek
        thinking = chunk.get('message', {}).get('thinking', '')
        if thinking:
            #logger.info(f"Thinking: {thinking}")
            pass
        
        if content:
            #logger.info(f"{logstr} response Content: {content}")
            yield content  # Yielding allows FastAPI to stream the data


@app.post("/chat/")
async def get_chat_stream(request: Request):
    # To get the raw body as bytes
    # To get the parsed JSON as a dictionary
    json_data = await request.json()
    requested_content = json_data.get("content", "")
    
    messages = [
        {"role": "system", "content": prompts['CHAT_PROMPT']},
        {"role": "user", "content": f"[INST]{requested_content}[INST]"}
    ]

    logger.info("Chat Stream log initiated")
    
    # Wrap the generator in a StreamingResponse so the client gets chunks
    return StreamingResponse(
        stream_content(messages), 
        media_type="text/text"
    )

@app.post("/intelligence/{engine_type}")
async def get_intelligence_stream(request: Request, engine_type: str):
    json_data = await request.json()
    requested_content = json_data.get("content", "")

    prompt_str = prompts['CHAT_PROMPT']

    if engine_type == "recovery":
        prompt_str = prompts['RECOVERY_PROMPT']
    elif engine_type == "readiness":
        prompt_str = prompts['READINESS_PROMPT']
    elif engine_type == "risk":
        prompt_str = prompts['RISK_PROMPT']
    elif engine_type == "overall":
        prompt_str = prompts['OVERALL_PROMPT']
    else:
        prompt_str = prompts['CHAT_PROMPT']

    messages = [
        {"role": "system", "content": prompt_str},
        {"role": "user", "content": f"[INST]{requested_content}[INST]"}
    ]

    logger.info(f"LLM Stream log initiated {engine_type}")
    
    # Wrap the generator in a StreamingResponse so the client gets chunks
    return StreamingResponse(
        stream_content(messages, engine_type=engine_type), 
        media_type="text/json"
    )