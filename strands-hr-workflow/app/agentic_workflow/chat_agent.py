from strands import Agent

from app.agentic_workflow.instructions.chat_system_instructions import CHAT_SYSTEM_PROMPT
from app.agentic_workflow.model import build_model
from app.configuration.config import Settings


def build_chat_agent(settings: Settings, tools: list[object]) -> Agent:
    model = build_model(settings)
    return Agent(model, tools=tools, system_prompt=CHAT_SYSTEM_PROMPT)