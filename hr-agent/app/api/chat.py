import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.agents.orchestrator import create_orchestrator
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str
    content: str
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = "hr-agent"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = 0.2
    session_id: str | None = None


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "strands-hr-agent"


@router.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            ModelCard(id="hr-agent"),
            ModelCard(id=settings.openai_model),
        ],
    }


async def generate_stream_response(
    agent_output_text: str, model: str, completion_id: str
) -> AsyncGenerator[str, None]:
    created = int(time.time())
    words = agent_output_text.split(" ")
    for idx, word in enumerate(words):
        chunk_content = word if idx == len(words) - 1 else word + " "
        chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": chunk_content},
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {json.dumps(chunk)}\n\n"

    # Finish chunk
    final_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty")

    session_id = req.session_id or str(uuid.uuid4())
    last_user_message = next((m.content for m in reversed(req.messages) if m.role == "user"), None)
    if not last_user_message:
        raise HTTPException(status_code=400, detail="At least one user message is required")

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    try:
        agent = create_orchestrator(session_id=session_id)
        # Execute agent reasoning over tools and specialists
        agent_result = agent(last_user_message)
        response_text = str(agent_result)
    except Exception as e:
        logger.error(f"Error executing HR agent: {e}", exc_info=True)
        response_text = (
            f"I encountered an error processing your HR request: {str(e)}. "
            "Please ensure the configured model provider is reachable."
        )

    if req.stream:
        return StreamingResponse(
            generate_stream_response(response_text, req.model, completion_id),
            media_type="text/event-stream",
        )

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": len(last_user_message.split()),
            "completion_tokens": len(response_text.split()),
            "total_tokens": len(last_user_message.split()) + len(response_text.split()),
        },
    }
