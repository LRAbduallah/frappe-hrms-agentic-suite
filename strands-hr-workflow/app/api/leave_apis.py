import httpx
from fastapi import APIRouter, HTTPException
import random
import re
from pydantic import BaseModel, EmailStr

from app.configuration.config import get_settings
from app.database.repository import WorkflowRepository
from app.database.session import get_session_factory

router = APIRouter(prefix="/leaves", tags=["leaves"])


class LeaveBalance(BaseModel):
    total_leave_balance_allocated: int
    leave_balance_used_this_month: float
    leave_balance_remaining: float


class EmployeeLeave(BaseModel):
    employee_id: int
    employee_name: str
    employee_email: EmailStr
    total_leave_balance_allocated: int
    leave_balance_used_this_month: float
    leave_balance_remaining: float


class SendEmailRequest(BaseModel):
    employee_id: int
    employee_name: str
    employee_email: EmailStr
    subject: str
    body: str


class SendPendingEmailRequest(BaseModel):
    workflow_run_id: str
    event_id: int


class SendEmailResponse(BaseModel):
    status: str
    message: str




@router.get("/leave_balances", response_model=LeaveBalance)
async def get_leave() -> LeaveBalance:
    total_leave_balance_allocated = random.randint(8, 24)
    leave_balance_used_this_month = round(random.uniform(0, total_leave_balance_allocated), 1)
    leave_balance_remaining = round(total_leave_balance_allocated - leave_balance_used_this_month, 1)

    return LeaveBalance(
        total_leave_balance_allocated=total_leave_balance_allocated,
        leave_balance_used_this_month=leave_balance_used_this_month,
        leave_balance_remaining=leave_balance_remaining,
    )



@router.post("/send_email", response_model=SendEmailResponse)
async def send_email(payload: SendEmailRequest) -> SendEmailResponse:
    print("/n")
    print(payload.model_dump_json())
    return SendEmailResponse(
        status="sent",
        message=f"Email queued for {payload.employee_name} <{payload.employee_email}>",
    )


@router.post("/send_pending_email", response_model=SendEmailResponse)
async def send_pending_email(payload: SendPendingEmailRequest) -> SendEmailResponse:
    settings = get_settings()
    session_factory = get_session_factory(settings.DATABASE_URL)

    with session_factory() as session:
        event = WorkflowRepository(session).get_email_event(
            payload.workflow_run_id,
            payload.event_id,
        )
        if event is None:
            raise HTTPException(status_code=404, detail="Workflow email event was not found")
        if event.delivery_status != "pending_review":
            raise HTTPException(
                status_code=409,
                detail=f"Email event is already {event.delivery_status}",
            )

        employee_id_match = re.search(r"\d+$", event.employee_id)
        if employee_id_match is None:
            raise HTTPException(
                status_code=422,
                detail=f"Employee ID must end with a numeric identifier: {event.employee_id}",
            )
        provider_payload = {
            "employee_id": int(employee_id_match.group()),
            "employee_name": event.employee_name,
            "employee_email": event.employee_email,
            "subject": event.subject,
            "body": event.body,
        }

    provider_url = f"{settings.EMAIL_API_BASE_URL.rstrip('/')}/leaves/send_email"

    try:
        async with httpx.AsyncClient() as client:
            provider_response = await client.post(provider_url, json=provider_payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Email provider unavailable: {exc}") from exc

    if provider_response.status_code != 200:
        raise HTTPException(
            status_code=provider_response.status_code,
            detail="Email provider did not confirm delivery.",
        )

    with session_factory() as session:
        event = WorkflowRepository(session).set_email_event_status(
            payload.workflow_run_id,
            payload.event_id,
            "sent",
            provider_response.text or "Email provider returned HTTP 200.",
        )
        if event is None:
            raise HTTPException(status_code=404, detail="Workflow email event was not found")
        session.commit()

    return SendEmailResponse(
        status="sent",
        message=f"Email sent to {event.employee_name} <{event.employee_email}>",
    )
    