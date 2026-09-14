import logging
from typing import Any

from strands.tools.mcp import MCPClient

from app.agentic_workflow.chat_agent import build_chat_agent
from app.agentic_workflow.schemas.chat_schemas import (
    ChatMessageResponse,
    ChatSessionResponse,
    ChatTurnResponse,
)
from app.agentic_workflow.services.mcp_service import mcp_client
from app.configuration.config import Settings, get_settings
from app.database.chat_repository import ChatRepository
from app.database.session import get_session_factory

logger = logging.getLogger(__name__)


class ChatSessionNotFoundError(ValueError):
    pass


def create_chat_session(settings: Settings | None = None) -> ChatSessionResponse:
    settings = settings or get_settings()
    with get_session_factory(settings.DATABASE_URL)() as session:
        chat_session = ChatRepository(session).create_session()
        session.commit()
        return ChatSessionResponse.model_validate(chat_session)


def _tool_name(tool: object) -> str:
    if isinstance(tool, dict):
        return str(tool.get("name", "unknown"))
    return str(getattr(tool, "name", getattr(tool, "tool_name", "unknown")))


def _response_text(response: object) -> str:
    output = getattr(response, "output", None)
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        for key in ("text", "content", "message"):
            value = output.get(key)
            if isinstance(value, str):
                return value
    return str(response)


def _prompt(history: list[Any], content: str) -> str:
    history_lines = [f"{message.role}: {message.content}" for message in history]
    history_text = "\n".join(history_lines) or "(no previous conversation)"
    return f"Conversation history:\n{history_text}\n\nCurrent user message:\n{content}"


def _persist_failure(session_id: str, message: str, error: Exception, settings: Settings) -> None:
    try:
        with get_session_factory(settings.DATABASE_URL)() as session:
            repository = ChatRepository(session)
            chat_session = repository.get_session(session_id)
            if chat_session is None:
                return
            repository.append_message(
                session_id,
                "assistant",
                message,
                error_message=type(error).__name__,
            )
            repository.set_session_status(chat_session, "failed")
            session.commit()
    except Exception:
        logger.exception("Unable to persist chat failure", extra={"session_id": session_id})


def send_chat_message(
    session_id: str,
    content: str,
    settings: Settings | None = None,
) -> ChatTurnResponse:
    settings = settings or get_settings()
    with get_session_factory(settings.DATABASE_URL)() as session:
        repository = ChatRepository(session)
        chat_session = repository.get_session(session_id)
        if chat_session is None:
            raise ChatSessionNotFoundError(f"Chat session {session_id} was not found")
        history = repository.list_messages(session_id, settings.CHAT_HISTORY_LIMIT)
        repository.append_message(session_id, "user", content)
        session.commit()

    try:
        with mcp_client(settings) as client:
            tools = client.list_tools_sync()
            available_tools = [_tool_name(tool) for tool in tools]
            agent = build_chat_agent(settings, tools)
            response = agent(_prompt(history, content))
            assistant_text = _response_text(response)

        with get_session_factory(settings.DATABASE_URL)() as session:
            repository = ChatRepository(session)
            chat_session = repository.get_session(session_id)
            if chat_session is None:
                raise ChatSessionNotFoundError(f"Chat session {session_id} was not found")
            repository.append_message(
                session_id,
                "assistant",
                assistant_text,
                tool_metadata={"available_tools": available_tools},
            )
            repository.set_session_status(chat_session, "active")
            session.commit()
            messages = repository.list_messages(session_id, settings.CHAT_HISTORY_LIMIT)

        return ChatTurnResponse(
            session_id=session_id,
            status="success",
            assistant_response=assistant_text,
            messages=[ChatMessageResponse.model_validate(message) for message in messages],
            available_tools=available_tools,
        )
    except ChatSessionNotFoundError:
        raise
    except Exception as exc:
        logger.exception("Chat agent invocation failed", extra={"session_id": session_id})
        error_message = "The HR assistant could not complete this request. Please try again."
        _persist_failure(session_id, error_message, exc, settings)
        return ChatTurnResponse(
            session_id=session_id,
            status="error",
            error_message=error_message,
        )


def get_chat_session(
    session_id: str,
    settings: Settings | None = None,
) -> tuple[ChatSessionResponse, list[ChatMessageResponse]]:
    settings = settings or get_settings()
    with get_session_factory(settings.DATABASE_URL)() as session:
        repository = ChatRepository(session)
        chat_session = repository.get_session(session_id)
        if chat_session is None:
            raise ChatSessionNotFoundError(f"Chat session {session_id} was not found")
        messages = repository.list_messages(session_id, settings.CHAT_HISTORY_LIMIT)
        return (
            ChatSessionResponse.model_validate(chat_session),
            [ChatMessageResponse.model_validate(message) for message in messages],
        )