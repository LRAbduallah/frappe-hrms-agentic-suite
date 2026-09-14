import json
import os
import re
import uuid
from typing import Any

from strands import Agent
from strands.models.mistral import MistralModel
from strands_tools import http_request

from app.configuration.config import Settings, get_settings
from app.database.repository import WorkflowRepository
from app.database.session import get_session_factory
from app.agentic_workflow.callbacks.workflow_callback_handler import WorkflowCallbackHandler
from app.agentic_workflow.hooks.workflow_hooks import WorkflowHookProvider
from app.agentic_workflow.instructions.system_instructions import DRAFT_SYSTEM_PROMPT, WORKFLOW_SYSTEM_PROMPT
from app.agentic_workflow.schemas.workflow_schemas import (
    EmployeeLeave,
    LeaveEmailDraft,
    LeaveRiskAssessment,
    PendingReviewEmail,
    SendEmailRequest,
    WorkflowEmployeeResult,
    WorkflowSummary,
)
from app.agentic_workflow.skills.leave_email_skills import WORKFLOW_SKILLS_PLUGIN
from app.agentic_workflow.services.mcp_service import get_employee_leave_balances


_PENDING_REVIEWS: dict[str, PendingReviewEmail] = {}
_PENDING_REVIEW_RUN_IDS: dict[str, str] = {}


def _risk_category(risk: LeaveRiskAssessment) -> str:
    if risk.is_lop_risk:
        return "lop_risk"
    if risk.is_low_balance:
        return "low_balance"
    return "normal"


def _blocked_summary(run_id: str, reason: str) -> WorkflowSummary:
    return WorkflowSummary(
        status="blocked",
        workflow_run_id=run_id,
        blocked_reason=reason,
        total_employees_processed=0,
        sent_count=0,
        pending_review_count=0,
        failed_count=0,
        results=[],
    )


def _extract_body_from_tool_result(result: dict[str, Any]) -> str:
    for item in result.get("content", []):
        text = item.get("text", "")
        if text.startswith("Body: "):
            return text.removeprefix("Body: ").strip()
    raise ValueError("Unable to extract response body from http_request result")


def _call_http_tool(method: str, url: str, body: str | None = None) -> Any:
    tool_input: dict[str, Any] = {
        "method": method,
        "url": url,
        "headers": {"Accept": "application/json"},
    }
    if body is not None:
        tool_input["headers"]["Content-Type"] = "application/json"
        tool_input["body"] = body

    return http_request.http_request(
        {
            "name": "http_request",
            "toolUseId": f"http-{uuid.uuid4()}",
            "input": tool_input,
        }
    )


def _build_model(settings: Settings) -> MistralModel:
    return MistralModel(
        api_key=settings.MISTRAL_API_KEY,
        client_args={"server_url": settings.MISTRAL_SERVER_URL.strip()},
        model_id="ministral-3b-2512",
    )


def _build_draft_agent(settings: Settings) -> Agent:
    return Agent(
        _build_model(settings),
        system_prompt=DRAFT_SYSTEM_PROMPT,
        callback_handler=WorkflowCallbackHandler(),
        hooks=[WorkflowHookProvider(settings)],
        plugins=[WORKFLOW_SKILLS_PLUGIN],
    )


def assess_leave_risk(employee: EmployeeLeave, settings: Settings) -> LeaveRiskAssessment:
    allocated = max(employee.total_leave_balance_allocated, 1.0)
    ratio_remaining = employee.leave_balance_remaining / allocated
    is_low = (
        employee.leave_balance_remaining <= settings.LOW_LEAVE_THRESHOLD_DAYS
        or ratio_remaining <= settings.LOW_LEAVE_THRESHOLD_RATIO
    )
    is_lop = employee.leave_balance_remaining <= 0

    if is_lop:
        reason = "Leave balance is exhausted. Any additional leave may result in Loss of Pay."
    elif is_low:
        reason = "Leave balance is almost low. If exceeded, additional leave may result in Loss of Pay."
    else:
        reason = "Leave balance is healthy."

    return LeaveRiskAssessment(
        is_low_balance=is_low,
        is_lop_risk=is_lop,
        alert_reason=reason,
    )


def draft_leave_email(employee: EmployeeLeave, risk: LeaveRiskAssessment, settings: Settings) -> LeaveEmailDraft:
    draft_agent = _build_draft_agent(settings)
    prompt = f"""
Draft a leave summary email for this employee.

Employee details:
- Employee ID: {employee.employee_id}
- Employee Name: {employee.employee_name}
- Total Leave Allocated: {employee.total_leave_balance_allocated} days
- Leave Used This Month: {employee.leave_balance_used_this_month} days
- Leave Remaining: {employee.leave_balance_remaining} days
- Low Balance Alert: {risk.is_low_balance}
- LOP Risk: {risk.is_lop_risk}
- Alert Reason: {risk.alert_reason}

Formatting constraints:
1) Return valid JSON only: {{"subject": "...", "body": "..."}}
2) If low balance or LOP risk is true, include an explicit warning about Loss of Pay when leave is exceeded.
3) Signature must be exactly:
John Doe
HR Manager
""".strip()

    raw = str(draft_agent(prompt)).strip()
    try:
        payload = json.loads(raw)
        return LeaveEmailDraft.model_validate(payload)
    except Exception:
        fallback = (
            f"Hi {employee.employee_name},\n\n"
            "This is your leave update. "
            f"Allocated: {employee.total_leave_balance_allocated} days, "
            f"used this month: {employee.leave_balance_used_this_month} days, "
            f"remaining: {employee.leave_balance_remaining} days.\n\n"
            f"{risk.alert_reason}\n\n"
            "Regards,\n"
            "John Doe\n"
            "HR Manager"
        )
        return LeaveEmailDraft(subject=f"Leave update for {employee.employee_name}", body=fallback)


def _send_email(employee: EmployeeLeave, draft: LeaveEmailDraft, email_api_base_url: str) -> WorkflowEmployeeResult:
    employee_id_match = re.search(r"\d+$", employee.employee_id)
    if employee_id_match is None:
        raise ValueError(f"Employee ID must end with a numeric identifier: {employee.employee_id}")

    send_payload = SendEmailRequest(
        employee_id=int(employee_id_match.group()),
        employee_name=employee.employee_name,
        employee_email=employee.employee_email,
        subject=draft.subject,
        body=draft.body,
    ).model_dump(mode="json")

    post_result = _call_http_tool(
        method="POST",
        url=f"{email_api_base_url.rstrip('/')}/leaves/send_email",
        body=json.dumps(send_payload),
    )
    post_body = _extract_body_from_tool_result(post_result)
    post_data = json.loads(post_body)
    status = post_data.get("status", "failed")

    return WorkflowEmployeeResult(
        employee_id=employee.employee_id,
        employee_name=employee.employee_name,
        employee_email=employee.employee_email,
        status="sent" if status == "sent" else "failed",
        message=str(post_data.get("message", "No API message returned")),
    )


def trigger_leave_workflow() -> WorkflowSummary:
    settings = get_settings()

    if settings.BYPASS_TOOL_CONSENT:
        os.environ["BYPASS_TOOL_CONSENT"] = "true"

    session_factory = get_session_factory(settings.DATABASE_URL)
    with session_factory() as session:
        repository = WorkflowRepository(session)
        if not repository.can_start_workflow(settings.WORKFLOW_COOLDOWN_DAYS):
            reason = (
                f"Leave workflow cooldown is active for {settings.WORKFLOW_COOLDOWN_DAYS:g} days."
            )
            blocked_run = repository.create_run(
                settings.WORKFLOW_COOLDOWN_DAYS,
                status="blocked",
                reason=reason,
            )
            session.commit()
            return _blocked_summary(blocked_run.id, reason)

        workflow_run = repository.create_run(settings.WORKFLOW_COOLDOWN_DAYS)
        session.commit()

    email_api_base_url = settings.EMAIL_API_BASE_URL.rstrip("/")
    try:
        employees = get_employee_leave_balances(settings)
    except Exception as exc:
        with session_factory() as session:
            repository = WorkflowRepository(session)
            workflow_run = session.get(type(workflow_run), workflow_run.id)
            if workflow_run is not None:
                repository.finalize_run(
                    workflow_run,
                    total_employees=0,
                    sent_count=0,
                    pending_review_count=0,
                    failed_count=0,
                    status="failed",
                    reason=str(exc),
                )
                session.commit()
        raise

    results: list[WorkflowEmployeeResult] = []

    for employee in employees:
        risk = assess_leave_risk(employee, settings)
        draft = draft_leave_email(employee, risk, settings)

        if settings.HITL_ENABLED and (risk.is_low_balance or risk.is_lop_risk):
            _PENDING_REVIEWS[employee.employee_id] = PendingReviewEmail(
                employee=employee,
                draft=draft,
                risk=risk,
            )
            _PENDING_REVIEW_RUN_IDS[employee.employee_id] = workflow_run.id
            with session_factory() as session:
                repository = WorkflowRepository(session)
                persisted_run = session.get(type(workflow_run), workflow_run.id)
                if persisted_run is not None:
                    repository.record_email_event(
                        persisted_run,
                        employee,
                        draft.subject,
                        draft.body,
                        _risk_category(risk),
                        "pending_review",
                        "Low leave balance/LOP risk detected. Pending human approval.",
                    )
                    session.commit()
            results.append(
                WorkflowEmployeeResult(
                    employee_id=employee.employee_id,
                    employee_name=employee.employee_name,
                    employee_email=employee.employee_email,
                    status="pending_review",
                    message="Low leave balance/LOP risk detected. Pending human approval.",
                )
            )
            continue

        try:
            result = _send_email(employee, draft, email_api_base_url)
        except Exception as exc:
            result = WorkflowEmployeeResult(
                employee_id=employee.employee_id,
                employee_name=employee.employee_name,
                employee_email=employee.employee_email,
                status="failed",
                message=f"Failed to send email: {exc}",
            )
        with session_factory() as session:
            repository = WorkflowRepository(session)
            persisted_run = session.get(type(workflow_run), workflow_run.id)
            if persisted_run is not None:
                repository.record_email_event(
                    persisted_run,
                    employee,
                    draft.subject,
                    draft.body,
                    _risk_category(risk),
                    result.status,
                    result.message,
                )
                session.commit()
        results.append(result)

    sent_count = len([r for r in results if r.status == "sent"])
    pending_count = len([r for r in results if r.status == "pending_review"])
    failed_count = len([r for r in results if r.status == "failed"])

    with session_factory() as session:
        repository = WorkflowRepository(session)
        persisted_run = session.get(type(workflow_run), workflow_run.id)
        if persisted_run is not None:
            repository.finalize_run(
                persisted_run,
                total_employees=len(results),
                sent_count=sent_count,
                pending_review_count=pending_count,
                failed_count=failed_count,
            )
            session.commit()

    return WorkflowSummary(
        status="completed",
        workflow_run_id=workflow_run.id,
        total_employees_processed=len(results),
        sent_count=sent_count,
        pending_review_count=pending_count,
        failed_count=failed_count,
        results=results,
    )


def get_pending_reviews() -> list[PendingReviewEmail]:
    return list(_PENDING_REVIEWS.values())


def review_pending_email(employee_id: str, action: str) -> WorkflowEmployeeResult:
    settings = get_settings()
    email_api_base_url = settings.EMAIL_API_BASE_URL.rstrip("/")

    pending = _PENDING_REVIEWS.get(employee_id)
    if pending is None:
        raise ValueError(f"No pending email found for employee_id={employee_id}")

    if action == "reject":
        _PENDING_REVIEWS.pop(employee_id, None)
        run_id = _PENDING_REVIEW_RUN_IDS.pop(employee_id, None)
        if run_id is not None:
            with get_session_factory(settings.DATABASE_URL)() as session:
                WorkflowRepository(session).update_event_status(
                    run_id,
                    employee_id,
                    "rejected",
                    "Email draft rejected by human reviewer.",
                )
                session.commit()
        return WorkflowEmployeeResult(
            employee_id=pending.employee.employee_id,
            employee_name=pending.employee.employee_name,
            employee_email=pending.employee.employee_email,
            status="rejected",
            message="Email draft rejected by human reviewer.",
        )

    result = _send_email(pending.employee, pending.draft, email_api_base_url)
    _PENDING_REVIEWS.pop(employee_id, None)
    run_id = _PENDING_REVIEW_RUN_IDS.pop(employee_id, None)
    if run_id is not None:
        with get_session_factory(settings.DATABASE_URL)() as session:
            WorkflowRepository(session).update_event_status(
                run_id,
                employee_id,
                result.status,
                result.message,
            )
            session.commit()
    return result


def get_workflow_system_prompt() -> str:
    return WORKFLOW_SYSTEM_PROMPT
