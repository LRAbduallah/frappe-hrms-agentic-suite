from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.models.workflow import utc_now


class ChatRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_session(self) -> ChatSession:
        chat_session = ChatSession()
        self.session.add(chat_session)
        self.session.flush()
        return chat_session

    def get_session(self, session_id: str) -> ChatSession | None:
        return self.session.get(ChatSession, session_id)

    def set_session_status(self, chat_session: ChatSession, status: str) -> ChatSession:
        chat_session.status = status
        chat_session.updated_at = utc_now()
        self.session.flush()
        return chat_session

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        tool_metadata: dict | list | None = None,
        error_message: str | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            chat_session_id=session_id,
            role=role,
            content=content,
            tool_metadata=tool_metadata,
            error_message=error_message,
        )
        self.session.add(message)
        self.session.flush()
        return message

    def list_messages(self, session_id: str, limit: int = 5) -> list[ChatMessage]:
        messages = self.session.scalars(
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == session_id)
            .order_by(desc(ChatMessage.created_at), desc(ChatMessage.id))
            .limit(limit)
        ).all()
        return list(reversed(messages))