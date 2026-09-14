from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.chat_repository import ChatRepository
from app.models.base import Base


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine)


def test_chat_repository_returns_latest_messages_in_chronological_order() -> None:
    with make_session() as session:
        repository = ChatRepository(session)
        chat_session = repository.create_session()
        for index in range(6):
            repository.append_message(chat_session.id, "user", f"message-{index}")
        session.commit()

        messages = repository.list_messages(chat_session.id, limit=5)

        assert [message.content for message in messages] == [
            "message-1",
            "message-2",
            "message-3",
            "message-4",
            "message-5",
        ]


def test_chat_session_cascade_deletes_messages() -> None:
    with make_session() as session:
        repository = ChatRepository(session)
        chat_session = repository.create_session()
        repository.append_message(chat_session.id, "user", "remove me")
        session.commit()

        session.delete(chat_session)
        session.commit()

        assert repository.list_messages(chat_session.id) == []