from pathlib import Path

from app.agentic_workflow.instructions.chat_system_instructions import CHAT_SYSTEM_PROMPT
from app.agentic_workflow.services import chat_service
from app.configuration.config import Settings
from app.database.chat_repository import ChatRepository
from app.database.session import get_session_factory


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        MISTRAL_API_KEY="test-key",
        DATABASE_URL=f"sqlite:///{tmp_path / 'chat.db'}",
        CHAT_HISTORY_LIMIT=5,
    )


class FakeTool:
    def __init__(self, name: str):
        self.name = name


class FakeClient:
    def __init__(self, tools: list[FakeTool]):
        self.tools = tools
        self.active = False

    def __enter__(self):
        self.active = True
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.active = False

    def list_tools_sync(self):
        return self.tools


class FakeAgent:
    def __init__(self, client: FakeClient, prompts: list[str]):
        self.client = client
        self.prompts = prompts

    def __call__(self, prompt: str) -> str:
        assert self.client.active is True
        self.prompts.append(prompt)
        return "The answer is grounded in MCP data."


def initialize_database(settings: Settings) -> None:
    with get_session_factory(settings.DATABASE_URL)() as session:
        from app.models.base import Base

        Base.metadata.create_all(session.get_bind())


def test_send_chat_message_uses_discovered_tools_and_five_message_history(
    tmp_path: Path, monkeypatch
) -> None:
    settings = make_settings(tmp_path)
    initialize_database(settings)
    created = chat_service.create_chat_session(settings)
    prompts: list[str] = []
    client = FakeClient([FakeTool("hrms_find_employee"), FakeTool("hrms_get_leave_balance")])

    with get_session_factory(settings.DATABASE_URL)() as session:
        repository = ChatRepository(session)
        for index in range(6):
            repository.append_message(created.id, "user", f"old-{index}")
        session.commit()

    monkeypatch.setattr(chat_service, "mcp_client", lambda _: client)
    monkeypatch.setattr(
        chat_service,
        "build_chat_agent",
        lambda _, tools: FakeAgent(client, prompts) if tools == client.tools else None,
    )

    result = chat_service.send_chat_message(created.id, "current question", settings)

    assert result.status == "success"
    assert result.available_tools == ["hrms_find_employee", "hrms_get_leave_balance"]
    assert "old-0" not in prompts[0]
    assert "old-1" in prompts[0]
    assert "old-5" in prompts[0]
    assert "current question" in prompts[0]


def test_send_chat_message_persists_safe_failure(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    initialize_database(settings)
    created = chat_service.create_chat_session(settings)

    class FailingClient(FakeClient):
        def list_tools_sync(self):
            raise RuntimeError("MCP unavailable")

    monkeypatch.setattr(chat_service, "mcp_client", lambda _: FailingClient([]))

    result = chat_service.send_chat_message(created.id, "lookup my leave", settings)

    assert result.status == "error"
    assert result.error_message == "The HR assistant could not complete this request. Please try again."
    with get_session_factory(settings.DATABASE_URL)() as session:
        messages = ChatRepository(session).list_messages(created.id, limit=10)
        assert messages[-1].role == "assistant"
        assert messages[-1].error_message == "RuntimeError"


def test_chat_prompt_requires_tool_execution_for_attendance_summary() -> None:
    assert "frappe_list_documents" in CHAT_SYSTEM_PROMPT
    assert "Attendance DocType" in CHAT_SYSTEM_PROMPT
    assert 'status set to "Present"' in CHAT_SYSTEM_PROMPT
    assert "use today by default" in CHAT_SYSTEM_PROMPT
    assert "instead of asking the user to choose" in CHAT_SYSTEM_PROMPT