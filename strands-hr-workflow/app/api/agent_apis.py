from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.agentic_workflow.schemas.workflow_schemas import (
	PendingReviewsResponse,
	ReviewDecisionRequest,
	TriggerWorkflowRequest,
	WorkflowEmployeeResult,
	WorkflowSummary,
)
from app.agentic_workflow.services.workflow_service import (
	get_pending_reviews,
	review_pending_email,
	trigger_leave_workflow,
)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/trigger", response_model=WorkflowSummary)
async def trigger_agent_workflow(payload: TriggerWorkflowRequest) -> WorkflowSummary:
	try:
		return await run_in_threadpool(
			trigger_leave_workflow,
		)
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/pending-reviews", response_model=PendingReviewsResponse)
async def list_pending_reviews() -> PendingReviewsResponse:
	pending = await run_in_threadpool(get_pending_reviews)
	return PendingReviewsResponse(pending_reviews=pending)


@router.post("/pending-reviews/{employee_id}", response_model=WorkflowEmployeeResult)
async def decide_pending_review(employee_id: str, payload: ReviewDecisionRequest) -> WorkflowEmployeeResult:
	try:
		return await run_in_threadpool(
			review_pending_email,
			employee_id,
			payload.action,
		)
	except ValueError as exc:
		raise HTTPException(status_code=404, detail=str(exc)) from exc
	except Exception as exc:
		raise HTTPException(status_code=500, detail=str(exc)) from exc
