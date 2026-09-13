from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class ActionProposal(BaseModel):
    action: str = Field(description="Action description, e.g., 'Correct attendance' or 'Send email'")
    target: str = Field(description="Target entity, e.g. employee ID or record name")
    reason: str = Field(description="Business rationale for the proposed mutation")
    risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM)
    requires_approval: bool = Field(default=True)
    tool_name: str = Field(description="MCP tool to call upon approval")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameters to pass to the tool")


class ApprovalRequest(BaseModel):
    id: str
    session_id: str
    request_id: str | None = None
    user_id: str = "hr_user"
    action: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    approved_at: str | None = None
    approved_by: str | None = None
    result: Any | None = None
    preflight: dict[str, Any] | None = None


# --- Structured Output Models for Specialist Agents ---

class EmployeeInfo(BaseModel):
    employee_id: str
    name: str
    department: str | None = None
    designation: str | None = None
    status: str | None = None
    company: str | None = None
    reports_to: str | None = None


class EmployeeResult(BaseModel):
    employees: list[EmployeeInfo] = Field(default_factory=list)
    summary: str


class LeaveBalance(BaseModel):
    employee_id: str
    employee_name: str | None = None
    leave_type: str
    total_allocated: float = 0.0
    used_leaves: float = 0.0
    pending_leaves: float = 0.0
    balance: float = 0.0
    is_critically_low: bool = False


class LeaveAnalysis(BaseModel):
    employee_id: str | None = None
    balances: list[LeaveBalance] = Field(default_factory=list)
    critically_low_count: int = 0
    analysis: str
    recommendations: list[str] = Field(default_factory=list)


class AttendanceRecord(BaseModel):
    employee: str
    attendance_date: str
    status: str
    leave_type: str | None = None
    late_entry: bool = False
    early_exit: bool = False


class AttendanceSummary(BaseModel):
    employee_id: str
    period: str | None = None
    total_days: int = 0
    present_days: int = 0
    absent_days: int = 0
    late_days: int = 0
    leave_days: int = 0
    anomalies: list[str] = Field(default_factory=list)
    explanation: str


class CommunicationDraft(BaseModel):
    recipient_id: str
    recipient_name: str
    recipient_email: str | None = None
    subject: str
    body: str
    category: Literal["leave_warning", "attendance_alert", "general_update", "follow_up"]
    requires_approval: bool = True


class HRReport(BaseModel):
    title: str
    period: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    findings: list[str] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
