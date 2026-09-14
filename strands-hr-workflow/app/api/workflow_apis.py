from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.agentic_workflow.schemas.workflow_schemas import (
    WorkflowEmailEventListResponse,
    WorkflowEmailEventResponse,
    WorkflowEmailEventUpdate,
    WorkflowRunListResponse,
    WorkflowRunResponse,
    WorkflowSummary,
)
from app.agentic_workflow.services.workflow_service import trigger_leave_workflow
from app.configuration.config import get_settings
from app.database.repository import WorkflowRepository
from app.database.session import get_session_factory

router = APIRouter(prefix="/workflows", tags=["workflow audit"])


def _session_factory():
    return get_session_factory(get_settings().DATABASE_URL)


def _get_run_or_404(session, run_id: str):
    run = WorkflowRepository(session).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Workflow run {run_id} was not found")
    return run


@router.post("/trigger", response_model=WorkflowSummary)
async def create_workflow_run() -> WorkflowSummary:
    """Trigger a leave workflow and persist its run and email audit records."""
    try:
        return await run_in_threadpool(trigger_leave_workflow)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("", response_model=WorkflowRunListResponse)
async def list_workflow_runs(
    status: str | None = Query(default=None),
    workflow_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> WorkflowRunListResponse:
    def query():
        with _session_factory()() as session:
            runs, total = WorkflowRepository(session).list_runs(
                limit=limit,
                offset=offset,
                status=status,
                workflow_type=workflow_type,
            )
            return WorkflowRunListResponse(items=runs, total=total, limit=limit, offset=offset)

    return await run_in_threadpool(query)


@router.get("/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(run_id: str) -> WorkflowRunResponse:
    def query():
        with _session_factory()() as session:
            return _get_run_or_404(session, run_id)

    return await run_in_threadpool(query)


@router.delete("/{run_id}", status_code=204)
async def delete_workflow_run(run_id: str) -> None:
    def delete():
        with _session_factory()() as session:
            repository = WorkflowRepository(session)
            _get_run_or_404(session, run_id)
            repository.delete_run(run_id)
            session.commit()

    await run_in_threadpool(delete)


@router.get("/{run_id}/emails", response_model=WorkflowEmailEventListResponse)
async def list_workflow_emails(
    run_id: str,
    delivery_status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> WorkflowEmailEventListResponse:
    def query():
        with _session_factory()() as session:
            _get_run_or_404(session, run_id)
            events, total = WorkflowRepository(session).list_email_events(
                run_id,
                limit=limit,
                offset=offset,
                delivery_status=delivery_status,
            )
            return WorkflowEmailEventListResponse(
                items=events,
                total=total,
                limit=limit,
                offset=offset,
            )

    return await run_in_threadpool(query)


@router.get("/{run_id}/sent-emails", response_model=WorkflowEmailEventListResponse)
async def list_sent_workflow_emails(
    run_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> WorkflowEmailEventListResponse:
    def query():
        with _session_factory()() as session:
            _get_run_or_404(session, run_id)
            events, total = WorkflowRepository(session).list_email_events(
                run_id,
                limit=limit,
                offset=offset,
                delivery_status="sent",
            )
            return WorkflowEmailEventListResponse(
                items=events,
                total=total,
                limit=limit,
                offset=offset,
            )

    return await run_in_threadpool(query)


@router.get("/{run_id}/pending-emails", response_model=WorkflowEmailEventListResponse)
async def list_pending_workflow_emails(
    run_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> WorkflowEmailEventListResponse:
    def query():
        with _session_factory()() as session:
            _get_run_or_404(session, run_id)
            events, total = WorkflowRepository(session).list_email_events(
                run_id,
                limit=limit,
                offset=offset,
                delivery_status="pending_review",
            )
            return WorkflowEmailEventListResponse(
                items=events,
                total=total,
                limit=limit,
                offset=offset,
            )

    return await run_in_threadpool(query)


@router.get("/{run_id}/emails/{event_id}", response_model=WorkflowEmailEventResponse)
async def get_workflow_email(run_id: str, event_id: int) -> WorkflowEmailEventResponse:
    def query():
        with _session_factory()() as session:
            _get_run_or_404(session, run_id)
            event = WorkflowRepository(session).get_email_event(run_id, event_id)
            if event is None:
                raise HTTPException(status_code=404, detail=f"Email event {event_id} was not found")
            return event

    return await run_in_threadpool(query)


@router.patch("/{run_id}/emails/{event_id}", response_model=WorkflowEmailEventResponse)
async def update_workflow_email(
    run_id: str,
    event_id: int,
    payload: WorkflowEmailEventUpdate,
) -> WorkflowEmailEventResponse:
    def update():
        with _session_factory()() as session:
            event = WorkflowRepository(session).set_email_event_status(
                run_id,
                event_id,
                payload.delivery_status,
                payload.provider_message,
            )
            if event is None:
                raise HTTPException(status_code=404, detail=f"Email event {event_id} was not found")
            session.commit()
            return event

    return await run_in_threadpool(update)


@router.delete("/{run_id}/emails/{event_id}", status_code=204)
async def delete_workflow_email(run_id: str, event_id: int) -> None:
    def delete():
        with _session_factory()() as session:
            deleted = WorkflowRepository(session).delete_email_event(run_id, event_id)
            if not deleted:
                raise HTTPException(status_code=404, detail=f"Email event {event_id} was not found")
            session.commit()

    await run_in_threadpool(delete)
