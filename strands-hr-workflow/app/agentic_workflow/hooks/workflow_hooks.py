import logging

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import (
    AfterToolCallEvent,
    AfterToolsEvent,
    BeforeToolCallEvent,
)

from app.configuration.config import Settings, get_settings
from app.database.repository import WorkflowRepository
from app.database.session import get_session_factory


logger = logging.getLogger(__name__)


class WorkflowHookProvider(HookProvider):
    """Hook provider for lightweight workflow observability and guardrails."""

    _TERMINAL_FAILURE_KEY = "workflow_tool_terminal_failure"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(BeforeToolCallEvent, self.on_before_tool_call)
        registry.add_callback(AfterToolCallEvent, self.on_after_tool_call)
        registry.add_callback(AfterToolsEvent, self.on_after_tools)

    def on_before_tool_call(self, event: BeforeToolCallEvent) -> None:
        tool_name = event.tool_use.get("name")
        if tool_name == "run_leave_email_workflow" and not self._workflow_allowed():
            event.cancel_tool = (
                "Leave workflow skipped because the configured cooldown has not elapsed."
            )
            self._mark_terminal_failure(event.invocation_state, event.cancel_tool)
            return
        if tool_name in {"hrms_find_employee", "hrms_get_leave_balance"} and not event.tool_use.get("input"):
            event.cancel_tool = f"{tool_name} requires input"

    def on_after_tool_call(self, event: AfterToolCallEvent) -> None:
        if event.tool_use.get("name") != "run_leave_email_workflow":
            return

        failure_message = event.cancel_message
        if event.exception is not None:
            failure_message = f"Leave workflow failed: {event.exception}"
            logger.error(
                "Leave workflow tool raised an exception",
                exc_info=(
                    type(event.exception),
                    event.exception,
                    event.exception.__traceback__,
                ),
            )
        elif isinstance(event.result, dict) and event.result.get("status") == "error":
            detail = self._error_detail(event.result)
            failure_message = f"Leave workflow failed: {detail}"
            logger.error("Leave workflow tool returned an error result: %r", event.result)

        if failure_message:
            self._mark_terminal_failure(event.invocation_state, failure_message)

    def on_after_tools(self, event: AfterToolsEvent) -> None:
        failure_message = event.invocation_state.get(self._TERMINAL_FAILURE_KEY)
        if failure_message:
            event.end_turn = str(failure_message)

    def _mark_terminal_failure(self, invocation_state: dict, message: str) -> None:
        invocation_state[self._TERMINAL_FAILURE_KEY] = message
        request_state = invocation_state.setdefault("request_state", {})
        request_state[self._TERMINAL_FAILURE_KEY] = message

    @staticmethod
    def _error_detail(result: dict) -> str:
        content = result.get("content")
        if isinstance(content, list):
            details = [
                item.get("text")
                for item in content
                if isinstance(item, dict) and item.get("text")
            ]
            if details:
                return "; ".join(str(detail) for detail in details)
        return "See the workflow error log for the complete tool result."

    def _workflow_allowed(self) -> bool:
        factory = get_session_factory(self.settings.DATABASE_URL)
        with factory() as session:
            repository = WorkflowRepository(session)
            return repository.can_start_workflow(self.settings.WORKFLOW_COOLDOWN_DAYS)
