import os
from strands.models.openai import OpenAIModel
from app.config import settings


def get_model(temperature: float = 0.2) -> OpenAIModel:
    """Instantiate OpenAIModel configured for OpenAI or any OpenAI-compatible provider."""
    client_args = {
        "api_key": settings.openai_api_key or "dummy-key-for-local"
    }
    if settings.openai_base_url:
        client_args["base_url"] = settings.openai_base_url

    return OpenAIModel(
        model_id=settings.openai_model,
        client_args=client_args,
        params={"temperature": temperature},
    )
