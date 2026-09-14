import json
import logging
import re
import time
import uuid
from typing import Any, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.agents.orchestrator import create_orchestrator
from app.auth import require_agent_api_key
from app.config import settings
from app.governance.approvals import approval_store, reset_approval_session, set_approval_session
from app.memory.session_memory import SessionMemory

router = APIRouter(dependencies=[Depends(require_agent_api_key)])
logger = logging.getLogger(__name__)
_PROGRESS_ONLY_RE = re.compile(
    r"^\s*(?:let me|i(?:'m| am) going to|i(?:'ll| will)|allow me to)\b.*"
    r"\b(?:finali[sz]e|finish|complete|check|review|look up|investigate)\b"
    r".*[.!]?\s*$",
    re.IGNORECASE | re.DOTALL,
)


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
        "frappe_get_creation_plan": "the HRMS creation plan",
        "frappe_get_api_catalog": "the HRMS API map",
        "frappe_get_link_options": "valid HRMS options",
        "frappe_create_workflow": "a dependency workflow",
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


def _result_stop_reason(result: Any) -> str | None:
    metrics = getattr(result, "metrics", None)
    invocation = getattr(metrics, "latest_agent_invocation", None)
    reason = getattr(invocation, "stop_reason", None)
    if reason:
        return str(reason)
    if isinstance(result, dict):
        return result.get("stop_reason")
    return None


def _needs_continuation(result: Any, text: str) -> bool:
    """Continue only for an interrupted/progress-only answer, not a real question."""
    if not text.strip():
        return True
    if _result_stop_reason(result) in {
        "limit_turns",
        "limit_total_tokens",
        "limit_output_tokens",
    }:
        return True
    stripped = text.strip()
    if stripped.endswith("?"):
        return False
    return bool(_PROGRESS_ONLY_RE.match(stripped))


def _continuation_prompt(text: str) -> str:
    return (
        "Continue the same request now. Your previous response stopped before completing the work:\n"
        f"{text[-1200:]}\n\n"
        "Do not repeat progress narration or say that you will finish later. Use any remaining "
        "tools, complete every requested action, and then provide the concise final answer. If "
        "something truly blocks completion, name the exact blocker and the precise user input needed."
    )


async def generate_stream_response(
    prompt: str, model: str, completion_id: str, session_id: str
) -> AsyncGenerator[str, None]:
    created = int(time.time())
    session_token = set_approval_session(session_id)
    try:
        agent = create_orchestrator(session_id=session_id)
        yield _status_event("Planning your request")
        last_tool_name = None
        emitted_text = False
        current_prompt = prompt
        for continuation in range(settings.completion_continuation_limit + 1):
            pass_text = ""
            pass_result = None
            async for event in agent.stream_async(
                current_prompt,
                limits={"turns": settings.agent_turn_limit},
            ):
                current_tool = event.get("current_tool_use") if isinstance(event, dict) else None
                tool_name = current_tool.get("name") if isinstance(current_tool, dict) else None
                if tool_name and tool_name != last_tool_name:
                    last_tool_name = tool_name
                    yield _status_event(
                        f"Checking {_friendly_tool_name(tool_name)}",
                        tool_name,
                    )
                elif (
                    isinstance(event, dict)
                    and event.get("type") == "tool_result"
                    and last_tool_name
                ):
                    yield _status_event("Reviewing the HRMS result")

                text = event.get("data") if isinstance(event, dict) else None
                if isinstance(text, str) and text:
                    pass_text += text
                    emitted_text = True
                    if last_tool_name:
                        yield _status_event("Writing response")
                        last_tool_name = None
                    yield _stream_chunk(text, model, completion_id, created)
                if isinstance(event, dict) and event.get("result") is not None:
                    pass_result = event["result"]

            if not pass_text and pass_result is not None:
                pass_text = _final_result_text(pass_result)
                if pass_text and not emitted_text:
                    emitted_text = True
                    yield _stream_chunk(pass_text, model, completion_id, created)
            if not _needs_continuation(pass_result, pass_text) or continuation >= settings.completion_continuation_limit:
                break
            current_prompt = _continuation_prompt(pass_text)
            yield _status_event("Continuing to complete the request")
    except Exception as exc:
        logger.error(f"Error streaming HR agent response: {exc}", exc_info=True)
        error_text = (
            f"I encountered an error processing your HR request: {exc}. "
            "Please ensure the configured model provider is reachable."
        )
        yield _stream_chunk(error_text, model, completion_id, created)
    finally:
        reset_approval_session(session_token)

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
    memory = SessionMemory(session_id)
    failed_approvals = approval_store.recent_failures(session_id)[:3]
    if failed_approvals:
        failure_lines = []
        for item in failed_approvals:
            raw_result = item.result if isinstance(item.result, dict) else {}
            raw = raw_result.get("message", "execution failed") if raw_result else item.result
            message = str(raw)[:240]
            if raw_result.get("failed_step"):
                completed = ", ".join(
                    f"{step_id}={step_data.get('name') or step_data.get('created_name')}"
                    for step_id, step_data in raw_result.get("completed_steps", {}).items()
                )
                message = (
                    f"{message} failed_step={raw_result['failed_step']}; "
                    f"completed={completed or 'none'}"
                )[:400]
            failure_lines.append(f"- {item.action}: {message}")
            memory.record_failure(message)
        last_user_message = (
            f"{last_user_message}\n\n"
            "RECENT APPROVAL FAILURES (compact):\n"
            "Explain the failure, ask for corrected live values, and do not repeat the same payload:\n"
            + "\n".join(failure_lines)
        )
    working_memory = memory.context_block()
    if working_memory:
        last_user_message = f"{working_memory}\n\n{last_user_message}"

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

    session_token = set_approval_session(session_id)
    try:
        agent = create_orchestrator(session_id=session_id)
        # Execute agent reasoning over tools and specialists
        current_prompt = last_user_message
        response_text = ""
        for continuation in range(settings.completion_continuation_limit + 1):
            agent_result = agent(
                current_prompt,
                limits={"turns": settings.agent_turn_limit},
            )
            response_text = _final_result_text(agent_result) or str(agent_result)
            if (
                not _needs_continuation(agent_result, response_text)
                or continuation >= settings.completion_continuation_limit
            ):
                break
            current_prompt = _continuation_prompt(response_text)
    except Exception as e:
        logger.error(f"Error executing HR agent: {e}", exc_info=True)
        response_text = (
            f"I encountered an error processing your HR request: {str(e)}. "
            "Please ensure the configured model provider is reachable."
        )
    finally:
        reset_approval_session(session_token)

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
