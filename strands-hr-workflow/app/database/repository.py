from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import WorkflowEmailEvent, WorkflowRun
from app.models.workflow import utc_now


class WorkflowRepository:
    def __init__(self, session: Session):
        self.session = session

    def latest_completed_run(self, workflow_type: str = "leave") -> WorkflowRun | None:
        return self.session.scalar(
            select(WorkflowRun)
            .where(
                WorkflowRun.workflow_type == workflow_type,
                WorkflowRun.status == "completed",
                WorkflowRun.completed_at.is_not(None),
            )
            .order_by(desc(WorkflowRun.completed_at))
            .limit(1)
        )

    def cooldown_remaining(
        self,
        cooldown_days: float,
        workflow_type: str = "leave",
        now: datetime | None = None,
    ) -> timedelta:
        if cooldown_days <= 0:
            return timedelta(0)
        latest = self.latest_completed_run(workflow_type)
        if latest is None or latest.completed_at is None:
            return timedelta(0)
        current_time = now or utc_now()
        elapsed = current_time - latest.completed_at
        return max(timedelta(days=cooldown_days) - elapsed, timedelta(0))

    def can_start_workflow(self, cooldown_days: float, workflow_type: str = "leave") -> bool:
        return self.cooldown_remaining(cooldown_days, workflow_type) <= timedelta(0)

    def create_run(
        self,
        cooldown_days: float,
        status: str = "running",
        reason: str | None = None,
        workflow_type: str = "leave",
    ) -> WorkflowRun:
        run = WorkflowRun(
            workflow_type=workflow_type,
            status=status,
            cooldown_days=cooldown_days,
            started_at=utc_now() if status == "running" else None,
            completed_at=utc_now() if status in {"completed", "blocked", "failed"} else None,
            reason=reason,
        )
        self.session.add(run)
        self.session.flush()
        return run

    def record_email_event(
        self,
        run: WorkflowRun,
        employee: Any,
        subject: str,
        body: str,
        risk_category: str,
        delivery_status: str,
        provider_message: str | None = None,
    ) -> WorkflowEmailEvent:
        event = WorkflowEmailEvent(
            workflow_run_id=run.id,
            employee_id=str(employee.employee_id),
            employee_name=employee.employee_name,
            employee_email=str(employee.employee_email),
            subject=subject,
            body=body,
            allocated_leave=employee.total_leave_balance_allocated,
            used_leave=employee.leave_balance_used_this_month,
            remaining_leave=employee.leave_balance_remaining,
            risk_category=risk_category,
            delivery_status=delivery_status,
            provider_message=provider_message,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def finalize_run(
        self,
        run: WorkflowRun,
        *,
        total_employees: int,
        sent_count: int,
        pending_review_count: int,
        failed_count: int,
        status: str = "completed",
        reason: str | None = None,
    ) -> WorkflowRun:
        run.status = status
        run.completed_at = utc_now()
        run.total_employees = total_employees
        run.sent_count = sent_count
        run.pending_review_count = pending_review_count
        run.failed_count = failed_count
        run.reason = reason
        self.session.flush()
        return run

    def update_event_status(
        self,
        run_id: str,
        employee_id: str,
        delivery_status: str,
        provider_message: str | None = None,
    ) -> WorkflowEmailEvent | None:
        event = self.session.scalar(
            select(WorkflowEmailEvent)
            .where(
                WorkflowEmailEvent.workflow_run_id == run_id,
                WorkflowEmailEvent.employee_id == str(employee_id),
            )
            .order_by(desc(WorkflowEmailEvent.created_at))
            .limit(1)
        )
        if event is None:
            return None
        event.delivery_status = delivery_status
        event.provider_message = provider_message
        event.updated_at = utc_now()
        self.session.flush()
        return event

    def list_runs(
        self,
        *,
        limit: int,
        offset: int,
        status: str | None = None,
        workflow_type: str | None = None,
    ) -> tuple[list[WorkflowRun], int]:
        query = select(WorkflowRun)
        count_query = select(func.count()).select_from(WorkflowRun)
        filters = []
        if status is not None:
            filters.append(WorkflowRun.status == status)
        if workflow_type is not None:
            filters.append(WorkflowRun.workflow_type == workflow_type)
        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)
        runs = list(
            self.session.scalars(
                query.order_by(desc(WorkflowRun.triggered_at)).limit(limit).offset(offset)
            ).all()
        )
        total = self.session.scalar(count_query) or 0
        return runs, total

    def get_run(self, run_id: str) -> WorkflowRun | None:
        return self.session.get(WorkflowRun, run_id)

    def delete_run(self, run_id: str) -> bool:
        run = self.get_run(run_id)
        if run is None:
            return False
        self.session.delete(run)
        self.session.flush()
        return True

    def list_email_events(
        self,
        run_id: str,
        *,
        limit: int,
        offset: int,
        delivery_status: str | None = None,
    ) -> tuple[list[WorkflowEmailEvent], int]:
        query = select(WorkflowEmailEvent).where(WorkflowEmailEvent.workflow_run_id == run_id)
        count_query = select(func.count()).select_from(WorkflowEmailEvent).where(
            WorkflowEmailEvent.workflow_run_id == run_id
        )
        if delivery_status is not None:
            query = query.where(WorkflowEmailEvent.delivery_status == delivery_status)
            count_query = count_query.where(WorkflowEmailEvent.delivery_status == delivery_status)
        events = list(
            self.session.scalars(
                query.order_by(desc(WorkflowEmailEvent.created_at)).limit(limit).offset(offset)
            ).all()
        )
        total = self.session.scalar(count_query) or 0
        return events, total

    def get_email_event(self, run_id: str, event_id: int) -> WorkflowEmailEvent | None:
        return self.session.scalar(
            select(WorkflowEmailEvent).where(
                WorkflowEmailEvent.workflow_run_id == run_id,
                WorkflowEmailEvent.id == event_id,
            )
        )

    def delete_email_event(self, run_id: str, event_id: int) -> bool:
        event = self.get_email_event(run_id, event_id)
        if event is None:
            return False
        self.session.delete(event)
        self.session.flush()
        return True

    def set_email_event_status(
        self,
        run_id: str,
        event_id: int,
        delivery_status: str,
        provider_message: str | None,
    ) -> WorkflowEmailEvent | None:
        event = self.get_email_event(run_id, event_id)
        if event is None:
            return None
        event.delivery_status = delivery_status
        event.provider_message = provider_message
        event.updated_at = utc_now()
        self.session.flush()
        return event
