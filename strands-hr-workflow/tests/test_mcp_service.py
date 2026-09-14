import asyncio
from types import SimpleNamespace

from app.agentic_workflow.services import mcp_service


def test_mcp_transport_uses_bearer_token(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

    @mcp_service.asynccontextmanager
    async def fake_streamable_http_client(url, *, http_client):
        captured["url"] = url
        captured["http_client"] = http_client
        yield (object(), object(), lambda: None)

    monkeypatch.setattr(mcp_service.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(mcp_service, "streamable_http_client", fake_streamable_http_client)

    settings = SimpleNamespace(
        FRAPPE_MCP_URL="http://mcp.example.test/mcp",
        MCP_BEARER_TOKEN="test-bearer-token",
    )

    async def exercise_transport() -> None:
        async with mcp_service._authenticated_transport(settings):
            return

    asyncio.run(exercise_transport())

    assert captured["url"] == "http://mcp.example.test/mcp"
    assert captured["http_client"] is not None
    assert captured["headers"] == {"Authorization": "Bearer test-bearer-token"}