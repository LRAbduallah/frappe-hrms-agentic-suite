from types import SimpleNamespace

from app.agentic_workflow import model


def test_build_model_uses_openai_compatible_provider_settings(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeOpenAIModel:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(model, "OpenAIModel", FakeOpenAIModel)

    result = model.build_model(
        SimpleNamespace(
            OPENAI_API_KEY="provider-key",
            OPENAI_BASE_URL=" https://mantle.example/v1 ",
            OPENAI_MODEL="mantle-model",
        )
    )

    assert isinstance(result, FakeOpenAIModel)
    assert captured == {
        "model_id": "mantle-model",
        "client_args": {
            "api_key": "provider-key",
            "base_url": "https://mantle.example/v1",
        },
        "params": {"temperature": 0.2},
    }
