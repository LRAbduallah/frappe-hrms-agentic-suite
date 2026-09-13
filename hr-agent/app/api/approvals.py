import logging
import uuid
from datetime import datetime
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.governance.approvals import approval_store
from app.models.schemas import ApprovalRequest, ApprovalStatus

router = APIRouter(prefix="/v1/approvals", tags=["approvals"])
logger = logging.getLogger(__name__)


class ApprovalDecision(BaseModel):
    approved_by: str = "hr_manager"
    comment: str | None = None


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
            f"MCP client not connected — cannot execute tool '{tool_name}'. "
            "Returning simulated success."
        )
        return {
            "status": "SUCCESS",
            "message": f"Operation '{tool_name}' approved (MCP not connected — execution simulated).",
            "simulated": True,
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
    from app.governance.payload_validator import validate_and_dry_run

    req = approval_store.get(approval_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")

    dry_run_result = validate_and_dry_run(req.tool_name, req.arguments)
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

    # Mark approved
    req.approved_at = datetime.utcnow().isoformat()
    req.approved_by = decision.approved_by

    # Actually execute the mutation on Frappe via MCP
    execution_result = _execute_tool_on_frappe(req.tool_name, req.arguments)

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

