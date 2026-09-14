import logging
import os
import sys

from strands import Agent, tool
from strands.models.mistral import MistralModel

from app.configuration.config import Settings, get_settings
from app.agentic_workflow.callbacks.workflow_callback_handler import WorkflowCallbackHandler
from app.agentic_workflow.hooks.workflow_hooks import WorkflowHookProvider
from app.agentic_workflow.instructions.system_instructions import WORKFLOW_SYSTEM_PROMPT
from app.agentic_workflow.schemas.workflow_schemas import WorkflowSummary
from app.agentic_workflow.services.workflow_service import trigger_leave_workflow
from app.agentic_workflow.skills.leave_email_skills import WORKFLOW_SKILLS_PLUGIN


def configure_verbose_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("strands").setLevel(
        os.getenv("STRANDS_LOG_LEVEL", "INFO").upper()
    )
    for logger_name in (
        "httpcore",
        "httpx",
        "mcp",
        "strands.telemetry",
    ):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)


@tool
def run_leave_email_workflow() -> WorkflowSummary:
    """Trigger leave workflow: fetch leave data, draft emails, and send/pending based on risk."""
    return trigger_leave_workflow()


def build_leave_agent() -> Agent:
    settings = get_settings()
    model = MistralModel(
        api_key=settings.MISTRAL_API_KEY,
        client_args={"server_url": settings.MISTRAL_SERVER_URL.strip()},
        model_id="ministral-3b-2512",
    )

    agent = Agent(
        model,
        tools=[run_leave_email_workflow],
        system_prompt=WORKFLOW_SYSTEM_PROMPT,
        callback_handler=WorkflowCallbackHandler(),
        hooks=[WorkflowHookProvider(settings)],
        plugins=[WORKFLOW_SKILLS_PLUGIN],
    )
    return agent


agent: Agent | None = None


def _terminal_workflow_failure(response: object) -> str | None:
    state = getattr(response, "state", None)
    if isinstance(state, dict):
        failure = state.get(WorkflowHookProvider._TERMINAL_FAILURE_KEY)
        if failure:
            return str(failure)
    return None


if __name__ == "__main__":
    configure_verbose_logging()
    agent = build_leave_agent()
    try:
        response = agent(
            """
            Trigger the leave email workflow now.
            Use only the run_leave_email_workflow tool. Do not call MCP tools
            directly; the workflow tool performs the employee lookup, drafting,
            delivery, and human-review handling after the cooldown check.
            """
        )
    except Exception as exc:
        print(f"Leave workflow failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    failure = _terminal_workflow_failure(response)
    if failure:
        print(failure, file=sys.stderr)
        raise SystemExit(1)

    print("\nFinal workflow response:")
    print(response)
