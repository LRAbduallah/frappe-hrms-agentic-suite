from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.agentic_workflow.schemas.chat_schemas import (
    ChatMessageRequest,
    ChatSessionResponse,
    ChatTurnResponse,
)
from app.agentic_workflow.services.chat_service import (
    ChatSessionNotFoundError,
    create_chat_session,
    get_chat_session,
    send_chat_message,
)

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("", response_model=ChatSessionResponse)
async def create_chat() -> ChatSessionResponse:
    return await run_in_threadpool(create_chat_session)


@router.post("/{session_id}/messages", response_model=ChatTurnResponse)
async def send_message(session_id: str, payload: ChatMessageRequest) -> ChatTurnResponse:
    try:
        return await run_in_threadpool(send_chat_message, session_id, payload.content)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to process chat message") from exc


@router.get("/{session_id}", response_model=dict)
async def read_chat(session_id: str) -> dict:
    try:
        session, messages = await run_in_threadpool(get_chat_session, session_id)
        return {"session": session, "messages": messages}
    except ChatSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc