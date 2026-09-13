import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.agents.orchestrator import create_orchestrator
from app.auth import require_agent_api_key
from app.config import settings

router = APIRouter(dependencies=[Depends(require_agent_api_key)])
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


def _stream_chunk(
    content: str, model: str, completion_id: str, created: int
) -> str:
    chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content},
                "finish_reason": None,
            }
        ],
    }
    return f"data: {json.dumps(chunk)}\n\n"


def _final_stream_chunk(model: str, completion_id: str, created: int) -> str:
    chunk = {
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
    return f"data: {json.dumps(chunk)}\n\n"


def _status_event(message: str, tool_name: str | None = None) -> str:
    return f"data: {json.dumps({'agent_status': {'message': message, 'tool': tool_name}})}\n\n"


def _friendly_tool_name(tool_name: str) -> str:
    labels = {
        "employee_specialist": "employee records",
        "leave_attendance_specialist": "leave and attendance",
        "payroll_specialist": "payroll",
        "expense_specialist": "expense claims",
        "lifecycle_specialist": "employee lifecycle",
        "recruitment_specialist": "recruitment",
        "reporting_specialist": "HR reports",
        "communication_specialist": "HR communications",
        "frappe_get_document": "an HRMS record",
        "frappe_list_documents": "HRMS records",
        "frappe_get_doctype_schema": "the HRMS schema",
        "frappe_get_link_options": "valid HRMS options",
        "hrms_find_employee": "employee records",
        "hrms_search_employees": "employee records",
        "hrms_get_leave_balance": "leave balances",
        "hrms_get_attendance": "attendance records",
        "hrms_get_salary_slips": "salary records",
        "hrms_verify_dataset": "HR data",
    }
    return labels.get(tool_name, tool_name.replace("_", " "))


def _final_result_text(result: Any) -> str:
    """Extract text from Strands' final AgentResult when no delta was emitted."""
    message = getattr(result, "message", None)
    if message is None and isinstance(result, dict):
        message = result.get("message")
    content = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
    if not isinstance(content, list):
        return ""
    text_parts = []
    for item in content:
        text = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
        if isinstance(text, str):
            text_parts.append(text)
    return "".join(text_parts)


async def generate_stream_response(
    prompt: str, model: str, completion_id: str, session_id: str
) -> AsyncGenerator[str, None]:
    created = int(time.time())
    try:
        agent = create_orchestrator(session_id=session_id)
        yield _status_event("Planning your request")
        last_tool_name = None
        emitted_text = False
        async for event in agent.stream_async(prompt):
            current_tool = event.get("current_tool_use") if isinstance(event, dict) else None
            tool_name = current_tool.get("name") if isinstance(current_tool, dict) else None
            if tool_name and tool_name != last_tool_name:
                last_tool_name = tool_name
                yield _status_event(
                    f"Checking {_friendly_tool_name(tool_name)}",
                    tool_name,
                )
            elif event.get("type") == "tool_result" and last_tool_name:
                yield _status_event("Reviewing the HRMS result")

            text = event.get("data") if isinstance(event, dict) else None
            if isinstance(text, str) and text:
                emitted_text = True
                if last_tool_name:
                    yield _status_event("Writing response")
                    last_tool_name = None
                yield _stream_chunk(text, model, completion_id, created)
            elif isinstance(event, dict) and not emitted_text and event.get("result") is not None:
                final_text = _final_result_text(event["result"])
                if final_text:
                    emitted_text = True
                    yield _stream_chunk(final_text, model, completion_id, created)
    except Exception as exc:
        logger.error(f"Error streaming HR agent response: {exc}", exc_info=True)
        error_text = (
            f"I encountered an error processing your HR request: {exc}. "
            "Please ensure the configured model provider is reachable."
        )
        yield _stream_chunk(error_text, model, completion_id, created)

    yield _final_stream_chunk(model, completion_id, created)
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

    if req.stream:
        return StreamingResponse(
            generate_stream_response(
                last_user_message,
                req.model,
                completion_id,
                session_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

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
