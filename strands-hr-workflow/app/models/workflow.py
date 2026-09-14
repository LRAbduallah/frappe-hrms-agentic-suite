from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        Index("ix_workflow_runs_status_completed_at", "status", "completed_at"),
        Index("ix_workflow_runs_triggered_at", "triggered_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workflow_type: Mapped[str] = mapped_column(String(100), nullable=False, default="leave")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="running")
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cooldown_days: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_employees: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    email_events: Mapped[list["WorkflowEmailEvent"]] = relationship(
        back_populates="workflow_run",
        cascade="all, delete-orphan",
    )


class WorkflowEmailEvent(Base):
    __tablename__ = "workflow_email_events"
    __table_args__ = (
        Index("ix_workflow_email_events_workflow_run_id", "workflow_run_id"),
        Index("ix_workflow_email_events_employee_id", "employee_id"),
        Index("ix_workflow_email_events_status", "delivery_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[str] = mapped_column(String(255), nullable=False)
    employee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    employee_email: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    allocated_leave: Mapped[float] = mapped_column(Float, nullable=False)
    used_leave: Mapped[float] = mapped_column(Float, nullable=False)
    remaining_leave: Mapped[float] = mapped_column(Float, nullable=False)
    risk_category: Mapped[str] = mapped_column(String(30), nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    workflow_run: Mapped[WorkflowRun] = relationship(back_populates="email_events")
