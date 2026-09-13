import json
import logging
import uuid
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth import require_agent_api_key
from app.governance.approvals import approval_store
from app.models.schemas import ApprovalRequest, ApprovalStatus

router = APIRouter(
    prefix="/v1/approvals",
    tags=["approvals"],
    dependencies=[Depends(require_agent_api_key)],
)
logger = logging.getLogger(__name__)


class ApprovalDecision(BaseModel):
    approved_by: str = "hr_manager"
    comment: str | None = None


def _resolve_workflow_refs(value: Any, results: dict[str, dict[str, Any]]) -> Any:
    """Resolve {"$ref": "step_id.name"} values after prerequisite creation."""
    if isinstance(value, list):
        return [_resolve_workflow_refs(item, results) for item in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {"$ref"}:
        reference = value["$ref"]
        if not isinstance(reference, str) or "." not in reference:
            raise ValueError(f"Invalid workflow reference: {reference!r}")
        step_id, attribute = reference.split(".", 1)
        if step_id not in results:
            raise ValueError(f"Workflow reference points to incomplete step '{step_id}'.")
        resolved = results[step_id].get(attribute)
        if resolved in (None, ""):
            raise ValueError(f"Workflow step '{step_id}' did not produce '{attribute}'.")
        return resolved
    return {key: _resolve_workflow_refs(item, results) for key, item in value.items()}


def _execute_create_workflow(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Execute dependency-ordered creates and stop visibly at the first failure."""
    completed: dict[str, dict[str, Any]] = {}
    step_results: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        step_id = step.get("id", f"step-{index + 1}")
        try:
            fields = _resolve_workflow_refs(step["fields"], completed)
            result = _execute_tool_on_frappe(
                "frappe_create_document",
                {"doctype": step["doctype"], "fields": fields},
            )
            step_result = {
                "id": step_id,
                "doctype": step["doctype"],
                "result": result,
            }
            step_results.append(step_result)
            if result.get("status") != "SUCCESS":
                return {
                    "status": "ERROR",
                    "message": (
                        f"Workflow stopped at '{step_id}' after {len(step_results) - 1} "
                        "step(s) completed. Review the partial result before retrying."
                    ),
                    "failed_step": step_id,
                    "completed_steps": completed,
                    "steps": step_results,
                }
            completed[step_id] = {
                "name": result.get("created_name"),
                "created_name": result.get("created_name"),
            }
        except Exception as exc:
            logger.error("Workflow step %s failed", step_id, exc_info=True)
            return {
                "status": "ERROR",
                "message": f"Workflow stopped at '{step_id}': {exc}",
                "failed_step": step_id,
                "completed_steps": completed,
                "steps": step_results,
            }
    return {
        "status": "SUCCESS",
        "message": f"Workflow completed successfully ({len(step_results)} step(s)).",
        "completed_steps": completed,
        "steps": step_results,
    }


@router.get("", response_model=list[ApprovalRequest])
async def list_approvals(session_id: str | None = None):
    """List pending or past mutation approval requests."""
    return approval_store.list_all(session_id=session_id)


@router.get("/{approval_id}", response_model=ApprovalRequest)
async def get_approval(approval_id: str):
    """Retrieve details of a specific approval request."""
    req = approval_store.get(approval_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return req


def _execute_tool_on_frappe(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a mutation tool on Frappe via the MCP client.

    Normalizes arguments into the exact Pydantic schema required by Frappe MCP tools,
    reliably detects Frappe API / validation errors, and strips HTML markup from errors.
    """
    from app.mcp.manager import mcp_manager
    from app.governance.payload_validator import normalize_mcp_arguments, parse_mcp_tool_result

    # Handle local non-MCP tools (e.g. simulated email sender)
    if tool_name == "send_email":
        recipient = arguments.get("recipient_name") or arguments.get("recipient_id", "employee")
        subject = arguments.get("subject", "HR Notification")
        logger.info(f"[APPROVAL:EXECUTE] Simulated email sent to {recipient}: '{subject}'")
        return {
            "status": "SUCCESS",
            "message": f"HR Notification email successfully sent to {recipient} (Subject: '{subject}').",
            "executed_tool": tool_name,
            "arguments": arguments,
        }

    if not mcp_manager.client:
        logger.warning(
            f"MCP client not connected — cannot execute tool '{tool_name}'."
        )
        return {
            "status": "ERROR",
            "message": (
                f"Operation '{tool_name}' was not executed because the MCP gateway is unavailable. "
                "The approval remains recorded as failed and must be retried after MCP is healthy."
            ),
            "executed_tool": tool_name,
            "arguments": arguments,
        }

    # Normalize arguments to match Frappe MCP Pydantic schemas (params wrapper)
    normalized_args = normalize_mcp_arguments(tool_name, arguments)
    tool_use_id = f"approval-exec-{uuid.uuid4().hex[:12]}"

    try:
        logger.info(f"[APPROVAL:EXECUTE] Calling MCP tool '{tool_name}' with normalized args: {normalized_args}")
        raw_result = mcp_manager.client.call_tool_sync(
            tool_use_id=tool_use_id,
            name=tool_name,
            arguments=normalized_args,
        )

        # Parse and detect any Frappe API error, validation exception, or HTTP status error
        exec_result = parse_mcp_tool_result(raw_result, tool_name)
        exec_result["arguments"] = arguments
        exec_result["normalized_arguments"] = normalized_args

        if exec_result.get("status") == "SUCCESS" and tool_name == "frappe_create_document":
            response = json.loads(exec_result.get("frappe_response", "{}"))
            created_name = response.get("name") if isinstance(response, dict) else None
            if not created_name and isinstance(response, dict):
                created_name = (response.get("data") or {}).get("name")
            if not created_name:
                return {
                    "status": "ERROR",
                    "message": (
                        f"Frappe acknowledged '{tool_name}' but did not return the created document name. "
                        "The write cannot be confirmed."
                    ),
                    "executed_tool": tool_name,
                    "arguments": arguments,
                    "normalized_arguments": normalized_args,
                    "raw_result": exec_result.get("frappe_response"),
                }

            verification_raw = mcp_manager.client.call_tool_sync(
                tool_use_id=f"{tool_use_id}-verify",
                name="frappe_get_document",
                arguments={"params": {"doctype": normalized_args["params"]["doctype"], "name": created_name}},
            )
            verification = parse_mcp_tool_result(verification_raw, "frappe_get_document")
            if verification.get("status") != "SUCCESS":
                return {
                    "status": "ERROR",
                    "message": (
                        f"Document '{created_name}' was reported as created, but verification failed: "
                        f"{verification.get('message', 'unknown verification error')}"
                    ),
                    "executed_tool": tool_name,
                    "arguments": arguments,
                    "normalized_arguments": normalized_args,
                    "created_name": created_name,
                    "verification": verification,
                }
            exec_result["created_name"] = created_name
            exec_result["verification"] = verification

        if exec_result.get("status") == "SUCCESS":
            logger.info(f"[APPROVAL:EXECUTE] Tool '{tool_name}' executed successfully.")
        else:
            logger.error(f"[APPROVAL:EXECUTE] Tool '{tool_name}' returned error: {exec_result.get('message')}")

        return exec_result

    except Exception as e:
        logger.error(f"[APPROVAL:EXECUTE] Exception calling '{tool_name}': {e}", exc_info=True)
        return {
            "status": "ERROR",
            "message": f"Failed to execute '{tool_name}': {str(e)}",
            "executed_tool": tool_name,
            "arguments": arguments,
            "normalized_arguments": normalized_args,
        }


@router.post("/{approval_id}/dry-run", response_model=ApprovalRequest)
@router.get("/{approval_id}/dry-run", response_model=ApprovalRequest)
async def dry_run_approval(approval_id: str):
    """Execute an on-demand pre-flight validation and dry-run check for an approval request."""
    from app.governance.payload_validator import validate_and_dry_run, validate_create_workflow

    req = approval_store.get(approval_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")

    dry_run_result = (
        validate_create_workflow(req.arguments)
        if req.tool_name == "frappe_create_workflow"
        else validate_and_dry_run(req.tool_name, req.arguments)
    )
    req.preflight = dry_run_result
    approval_store.save(req)
    return req


@router.post("/{approval_id}/approve", response_model=ApprovalRequest)
async def approve_request(approval_id: str, decision: ApprovalDecision):
    """Approve and execute a queued mutation on Frappe."""
    req = approval_store.get(approval_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if req.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Request is already in state {req.status}")

    if req.tool_name.startswith("frappe_") or req.tool_name.startswith("hrms_"):
        from app.governance.payload_validator import validate_and_dry_run, validate_create_workflow

        req.preflight = (
            validate_create_workflow(req.arguments)
            if req.tool_name == "frappe_create_workflow"
            else validate_and_dry_run(req.tool_name, req.arguments)
        )
        if not req.preflight.get("dry_run_passed", False):
            req.status = ApprovalStatus.FAILED
            req.result = {
                "status": "ERROR",
                "message": "Approval was not executed because pre-flight validation failed.",
                "errors": req.preflight.get("errors", []),
            }
            approval_store.save(req)
            logger.error("Approval %s blocked by pre-flight validation: %s", approval_id, req.preflight)
            return req

    # Atomically claim the request so double-clicks or concurrent API retries
    # cannot execute the same mutation twice.
    claimed = approval_store.claim_for_execution(approval_id, decision.approved_by)
    if not claimed:
        raise HTTPException(
            status_code=409,
            detail="Approval was already claimed or is no longer pending.",
        )
    req = claimed

    # Actually execute the mutation on Frappe via MCP
    execution_result = (
        _execute_create_workflow(req.arguments["steps"])
        if req.tool_name == "frappe_create_workflow"
        else _execute_tool_on_frappe(req.tool_name, req.arguments)
    )

    if execution_result.get("status") == "SUCCESS":
        req.status = ApprovalStatus.EXECUTED
        req.result = execution_result
        logger.info(f"Approved and executed action {approval_id}: {req.action}")
    else:
        req.status = ApprovalStatus.FAILED
        req.result = execution_result
        logger.error(f"Approved but execution failed for {approval_id}: {execution_result}")

    approval_store.save(req)
    return req


@router.post("/{approval_id}/reject", response_model=ApprovalRequest)
async def reject_request(approval_id: str, decision: ApprovalDecision):
    """Reject a proposed mutation."""
    req = approval_store.get(approval_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if req.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Request is already in state {req.status}")

    req.status = ApprovalStatus.REJECTED
    req.approved_at = datetime.utcnow().isoformat()
    req.approved_by = decision.approved_by
    req.result = {"status": "REJECTED", "comment": decision.comment}
    approval_store.save(req)
    logger.info(f"Rejected action {approval_id}: {req.action}")
    return req
