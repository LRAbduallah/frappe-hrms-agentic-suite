from typing import Literal

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class EmployeeLeave(BaseModel):
    employee_id: str
    employee_name: str
    employee_email: EmailStr
    total_leave_balance_allocated: float
    leave_balance_used_this_month: float
    leave_balance_remaining: float


class MCPEmployee(BaseModel):
    employee: str
    employee_name: str
    employee_email: EmailStr


class MCPLeaveBalance(BaseModel):
    employee: str
    total_leave_balance_allocated: float
    leave_balance_remaining: float
    leave_balance_used_this_month: float = 0.0


class LeaveRiskAssessment(BaseModel):
    is_low_balance: bool
    is_lop_risk: bool
    alert_reason: str


class LeaveEmailDraft(BaseModel):
    subject: str
    body: str


class SendEmailRequest(BaseModel):
    employee_id: int
    employee_name: str
    employee_email: EmailStr
    subject: str
    body: str


class PendingReviewEmail(BaseModel):
    employee: EmployeeLeave
    draft: LeaveEmailDraft
    risk: LeaveRiskAssessment


class WorkflowEmployeeResult(BaseModel):
    employee_id: str
    employee_name: str
    employee_email: EmailStr
    status: Literal["sent", "pending_review", "rejected", "failed"]
    message: str


class WorkflowSummary(BaseModel):
    status: Literal["completed", "blocked", "failed"] = "completed"
    workflow_run_id: str | None = None
    blocked_reason: str | None = None
    total_employees_processed: int
    sent_count: int
    pending_review_count: int
    failed_count: int
    results: list[WorkflowEmployeeResult]


class TriggerWorkflowRequest(BaseModel):
    pass


class ReviewDecisionRequest(BaseModel):
    action: Literal["approve", "reject"]


class PendingReviewsResponse(BaseModel):
    pending_reviews: list[PendingReviewEmail]


class WorkflowEmailEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_run_id: str
    employee_id: str
    employee_name: str
    employee_email: EmailStr
    subject: str
    body: str
    allocated_leave: float
    used_leave: float
    remaining_leave: float
    risk_category: str
    delivery_status: str
    provider_message: str | None
    created_at: datetime
    updated_at: datetime


class WorkflowRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_type: str
    status: str
    triggered_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    cooldown_days: float
    total_employees: int
    sent_count: int
    pending_review_count: int
    failed_count: int
    reason: str | None


class WorkflowRunListResponse(BaseModel):
    items: list[WorkflowRunResponse]
    total: int
    limit: int
    offset: int


class WorkflowEmailEventListResponse(BaseModel):
    items: list[WorkflowEmailEventResponse]
    total: int
    limit: int
    offset: int


class WorkflowEmailEventUpdate(BaseModel):
    delivery_status: Literal["sent", "pending_review", "rejected", "failed"]
    provider_message: str | None = None
