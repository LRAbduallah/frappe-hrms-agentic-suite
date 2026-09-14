from strands.models.openai import OpenAIModel

from app.configuration.config import Settings


def build_model(settings: Settings, temperature: float = 0.2) -> OpenAIModel:
    client_args = {"api_key": settings.OPENAI_API_KEY}
    if settings.OPENAI_BASE_URL and settings.OPENAI_BASE_URL.strip():
        client_args["base_url"] = settings.OPENAI_BASE_URL.strip()

    return OpenAIModel(
        model_id=settings.OPENAI_MODEL,
        client_args=client_args,
        params={"temperature": temperature},
    )
