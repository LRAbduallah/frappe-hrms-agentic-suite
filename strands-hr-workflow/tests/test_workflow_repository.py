from datetime import timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database.repository import WorkflowRepository
from app.models.base import Base
from app.models.workflow import WorkflowEmailEvent, WorkflowRun, utc_now


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine)


def test_cooldown_zero_and_elapsed_window() -> None:
    with make_session() as session:
        repository = WorkflowRepository(session)
        assert repository.can_start_workflow(0) is True

        run = repository.create_run(15, status="completed")
        run.completed_at = utc_now() - timedelta(days=15)
        session.commit()

        assert repository.can_start_workflow(15) is True


def test_cooldown_blocks_recent_completed_run() -> None:
    with make_session() as session:
        repository = WorkflowRepository(session)
        run = repository.create_run(15, status="completed")
        run.completed_at = utc_now() - timedelta(days=1)
        session.commit()

        assert repository.can_start_workflow(15) is False
        blocked = repository.create_run(15, status="blocked", reason="cooldown")
        session.commit()

        persisted = session.get(WorkflowRun, blocked.id)
        assert persisted is not None
        assert persisted.status == "blocked"
        assert persisted.reason == "cooldown"


def test_email_event_can_be_updated_after_review() -> None:
    with make_session() as session:
        repository = WorkflowRepository(session)
        run = repository.create_run(0)
        employee = type(
            "Employee",
            (),
            {
                "employee_id": "EMP-1",
                "employee_name": "Test Employee",
                "employee_email": "test@example.com",
                "total_leave_balance_allocated": 20.0,
                "leave_balance_used_this_month": 4.0,
                "leave_balance_remaining": 16.0,
            },
        )()
        event = repository.record_email_event(
            run,
            employee,
            "Leave update",
            "Full email body",
            "normal",
            "sent",
            "queued",
        )
        session.commit()

        updated = repository.update_event_status(run.id, "EMP-1", "rejected", "Rejected")
        session.commit()

        assert updated is not None
        assert updated.id == event.id
        persisted = session.scalar(select(WorkflowEmailEvent).where(WorkflowEmailEvent.id == event.id))
        assert persisted is not None
        assert persisted.body == "Full email body"
        assert persisted.delivery_status == "rejected"
