import logging
from strands import Agent
from strands.session.file_session_manager import FileSessionManager
from app.agents.specialists import (
    create_employee_agent,
    create_leave_attendance_agent,
    create_payroll_agent,
    create_expense_agent,
    create_lifecycle_agent,
    create_recruitment_agent,
    create_reporting_agent,
    create_communication_agent,
)
from app.agents.context import conversation_manager
from app.config import settings
from app.hooks.governance import HRAgentGovernanceHook
from app.models.llm import get_model

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the HR Operations Orchestrator for Frappe HRMS. Route work to specialists; do not dump schemas.

## Specialists
1. employee_specialist — employees, departments, designations, grades, branches
2. leave_attendance_specialist — leave, attendance, shifts
3. payroll_specialist — salary slips, structures, payroll, advances
4. expense_specialist — expense claims, travel
5. lifecycle_specialist — onboarding, separation, transfer, promotion
6. recruitment_specialist — openings, applicants, interviews, offers
7. reporting_specialist — analytics and summaries
8. communication_specialist — draft emails (approval required)

## Rules
- Use the fewest specialists that can complete the request. Prefer one.
- Mutations require human approval. Never claim a Frappe write succeeded until approval executes.
- Never invent Company, Employee, Department, Designation, Leave Type, or other Link values.
- If multiple valid linked records exist, ask the user to choose.
- Keep answers concise. Do not paste catalogs, schemas, or large option lists into chat.
- When asked what you can do, summarize the specialist list. Do not list MCP tools.
- Working memory and recent approval failures, if provided, are authoritative for this turn.
"""


def create_orchestrator(session_id: str | None = None) -> Agent:
    """Create the Main HR Operations Orchestrator with all Specialists mounted via as_tool()."""
    model = get_model()

    # Instantiate all specialists
    emp_agent = create_employee_agent()
    leave_agent = create_leave_attendance_agent()
    payroll_agent = create_payroll_agent()
    expense_agent = create_expense_agent()
    lifecycle_agent = create_lifecycle_agent()
    recruitment_agent = create_recruitment_agent()
    rep_agent = create_reporting_agent()
    comm_agent = create_communication_agent()

    # Expose specialists as tools using Strands agents-as-tools
    tools = [
        emp_agent.as_tool(
            name="employee_specialist",
            description=(
                "Look up or manage employees, departments, designations, grades, branches, employment types. "
                "Can also create or update Employee master records."
            ),
        ),
        leave_agent.as_tool(
            name="leave_attendance_specialist",
            description=(
                "Check leave balances, allocations, policies; query attendance and check-in logs; "
                "manage shift assignments; create Leave Applications, Leave Policies, Leave Encashments; "
                "propose attendance corrections."
            ),
        ),
        payroll_agent.as_tool(
            name="payroll_specialist",
            description=(
                "Query or generate salary slips, run payroll entries, manage salary structures and components, "
                "create additional salary (bonus/deductions), manage employee advances and loans."
            ),
        ),
        expense_agent.as_tool(
            name="expense_specialist",
            description=(
                "Create or query Expense Claims, Travel Requests, and expense type classifications. "
                "Draft reimbursement claims with line items."
            ),
        ),
        lifecycle_agent.as_tool(
            name="lifecycle_specialist",
            description=(
                "Manage employee lifecycle events: onboarding checklists, separation/offboarding workflows, "
                "internal transfers, promotions, and exit interviews."
            ),
        ),
        recruitment_agent.as_tool(
            name="recruitment_specialist",
            description=(
                "Post job openings, track applicants, schedule interviews, capture feedback, "
                "generate job offers, and review staffing plans."
            ),
        ),
        rep_agent.as_tool(
            name="reporting_specialist",
            description=(
                "Generate cross-domain HR analytics: headcount summaries, leave utilization, "
                "attendance anomalies, payroll distribution, recruitment funnel metrics."
            ),
        ),
        comm_agent.as_tool(
            name="communication_specialist",
            description=(
                "Draft personalized HR email notifications (leave warnings, payroll updates, "
                "onboarding/offboarding communications). All emails require approval before sending."
            ),
        ),
    ]

    session_manager = None
    if session_id:
        session_manager = FileSessionManager(
            session_id=session_id,
            storage_dir=settings.session_storage_path,
        )

    return Agent(
        name="hr_orchestrator",
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        session_manager=session_manager,
        conversation_manager=conversation_manager(),
        hooks=[HRAgentGovernanceHook()],
    )
