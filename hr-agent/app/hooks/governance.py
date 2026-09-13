import logging
import time
from typing import Any
from strands.hooks import (
    HookProvider,
    HookRegistry,
    BeforeInvocationEvent,
    AfterInvocationEvent,
    BeforeToolCallEvent,
    AfterToolCallEvent,
)

logger = logging.getLogger("hr_agent.audit")
_LOG_CLIP = 400


def _clip(value: Any, limit: int = _LOG_CLIP) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [truncated {len(text) - limit} chars]"

# Tools requiring human approval before mutation
MUTATION_TOOLS = {
    "frappe_create_document",
    "frappe_update_document",
    "frappe_submit_document",
    "frappe_cancel_document",
    "hrms_apply_leave",
    "hrms_mark_attendance",
    "hrms_create_salary_slip",
    "send_email",
}

# Dangerous operations disabled entirely for governance
DISABLED_TOOLS = {
    "frappe_delete_document",
    "frappe_bulk_create_documents",
}


class HRAgentGovernanceHook(HookProvider):
    """Strands Hook Provider for Request Logging, Audit Trail, and Mutation Enforcement."""

    def __init__(self):
        self._start_times: dict[str, float] = {}

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.on_before_invocation)
        registry.add_callback(AfterInvocationEvent, self.on_after_invocation)
        registry.add_callback(BeforeToolCallEvent, self.on_before_tool_call)
        registry.add_callback(AfterToolCallEvent, self.on_after_tool_call)

    def on_before_invocation(self, event: BeforeInvocationEvent) -> None:
        agent_name = getattr(event.agent, "name", "Agent")
        self._start_times[str(id(event))] = time.time()
        logger.info(f"[AUDIT] Starting invocation on {agent_name}")

    def on_after_invocation(self, event: AfterInvocationEvent) -> None:
        agent_name = getattr(event.agent, "name", "Agent")
        start_time = self._start_times.pop(str(id(event)), None)
        duration = round(time.time() - start_time, 3) if start_time else 0.0
        logger.info(f"[AUDIT] Completed invocation on {agent_name} in {duration}s")

    def on_before_tool_call(self, event: BeforeToolCallEvent) -> None:
        tool_use = event.tool_use or {}
        tool_name = tool_use.get("name", "")
        tool_args = tool_use.get("input", {})
        logger.info(
            "[AUDIT:TOOL:BEFORE] tool=%s tool_use_id=%s args=%s",
            tool_name,
            tool_use.get("toolUseId", ""),
            _clip(tool_args),
        )

        # Enforce disabled tools
        if tool_name in DISABLED_TOOLS:
            logger.warning(f"[GOVERNANCE:DENIED] Tool '{tool_name}' is disabled by safety policy.")
            raise PermissionError(f"Action '{tool_name}' is disabled for safety.")

        # Enforce mutation tools — they must go through propose_* approval flow
        if tool_name in MUTATION_TOOLS:
            logger.warning(
                f"[GOVERNANCE:BLOCKED] Direct call to mutation tool '{tool_name}' blocked. "
                "Must use propose_create_document, propose_update_document, or propose_send_email instead."
            )
            raise PermissionError(
                f"Direct call to '{tool_name}' is not allowed. All mutations require human approval. "
                "Use propose_create_document, propose_update_document, propose_attendance_correction, "
                "or propose_send_email to queue the action for approval."
            )

    def on_after_tool_call(self, event: AfterToolCallEvent) -> None:
        tool_use = event.tool_use or {}
        tool_name = tool_use.get("name", "")
        tool_args = tool_use.get("input", {})
        result = event.result
        logger.info(
            "[AUDIT:TOOL:AFTER] tool=%s tool_use_id=%s args=%s result=%s",
            tool_name,
            tool_use.get("toolUseId", ""),
            _clip(tool_args),
            _clip(result, 800),
        )
