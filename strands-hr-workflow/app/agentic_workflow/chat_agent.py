from strands import Agent
from strands.models.mistral import MistralModel

from app.agentic_workflow.instructions.chat_system_instructions import CHAT_SYSTEM_PROMPT
from app.configuration.config import Settings


def build_chat_agent(settings: Settings, tools: list[object]) -> Agent:
    model = MistralModel(
        api_key=settings.MISTRAL_API_KEY,
        client_args={"server_url": settings.MISTRAL_SERVER_URL.strip()},
        model_id="ministral-3b-2512",
    )
    return Agent(model, tools=tools, system_prompt=CHAT_SYSTEM_PROMPT)