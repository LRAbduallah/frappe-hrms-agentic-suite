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
from app.config import settings
from app.hooks.governance import HRAgentGovernanceHook
from app.models.llm import get_model

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the central HR Operations Orchestrator for Frappe HRMS.
You have full access to all HRMS capabilities through specialized agents.

## Your Specialists

1. **employee_specialist** — Employee master records, directory, departments, designations, grades, branches.
   Can also CREATE and UPDATE employee records.

2. **leave_attendance_specialist** — Leave balances, allocations, policies, holiday lists, leave applications.
   Attendance records, check-in/out logs, shift assignments, attendance corrections.
   Can CREATE: Leave Application, Leave Allocation, Leave Policy, Leave Policy Assignment,
   Compensatory Leave Request, Leave Encashment, Shift Assignment.

3. **payroll_specialist** — Salary slips, salary structures, payroll entries, salary components,
   additional salary (bonus/deduction), employee advances, loans, income tax slabs, benefit claims.
   Can CREATE: Salary Slip, Payroll Entry, Salary Structure Assignment, Additional Salary, Employee Advance.

4. **expense_specialist** — Expense claims, expense types, travel requests, reimbursements.
   Can CREATE: Expense Claim, Travel Request.

5. **lifecycle_specialist** — Employee onboarding checklists, separations/resignations, internal transfers,
   promotions, and exit interviews.
   Can CREATE: Employee Onboarding, Employee Separation, Employee Transfer, Employee Promotion.

6. **recruitment_specialist** — Job openings, candidates, interviews, interview feedback, job offers, staffing plans.
   Can CREATE: Job Opening, Job Applicant, Interview, Interview Feedback, Job Offer.

7. **reporting_specialist** — Cross-domain HR analytics: headcount, leave utilization, attendance anomalies,
   payroll summaries, recruitment funnel metrics.

8. **communication_specialist** — Draft and propose personalized HR email notifications (require approval).

## Rules

- Route each request to the most appropriate specialist(s). Combine specialists for cross-domain tasks.
- All mutations (create, update, submit) are HITL-gated: they require human approval before any Frappe write.
- Before any document creation or update, use `frappe_get_creation_plan` against the live Frappe
  instance. Use its required fields, child-table structure, prerequisites, and real Link options.
- Never invent a Company, Employee, Department, Designation, Leave Type, Currency, Cost Center,
  or other linked value. If multiple valid options are returned, ask the user to choose; if no
  valid option exists, explain the missing prerequisite and do not create a partial document.
- Clearly distinguish retrieved FACTS from ANALYSIS or RECOMMENDATIONS.
- When an operation queues an approval, inform the user: "✅ An approval request has been created."
- Be concise, professional, and structured in your responses.
- Use markdown formatting for lists, tables, and structured data.

## Responding to "What can you do?" or capability questions

When the user asks what you can do, return a comprehensive response using this structure:

### 👤 Employee Management
- Search, view, create, and update employee profiles (personal info, department, designation, grade, branch)
- Manage departments, designations, grades, branches, employment types, employee groups

### 📅 Leave & Attendance
- Check leave balances, allocations, and leave policies
- Create Leave Applications, Leave Allocations, Leave Policies, Leave Policy Assignments
- Record Compensatory Leave Requests and Leave Encashments
- View and correct daily attendance records; manage shift assignments

### 💰 Payroll & Compensation
- View salary slips and salary structures
- Generate salary slips and run payroll entries (batch processing)
- Create Salary Structure Assignments, Additional Salary (bonus/deductions), Employee Advances, Loans
- Review income tax slabs and employee benefit claims

### 🧾 Expense Claims & Travel
- Create and track Expense Claims (with line item breakdown)
- Submit Travel Request pre-authorizations
- Query expense types and reimbursement history

### 🔄 Employee Lifecycle
- Initiate onboarding checklists for new joiners
- Process separation/offboarding workflows (resignations, terminations)
- Record internal transfers, promotions, and exit interviews

### 🎯 Recruitment
- Post Job Openings and track applicants
- Schedule interviews and capture interview feedback
- Generate Job Offers; manage staffing plans

### 📊 Reports & Analytics
- Department headcount and org structure summaries
- Leave utilization and absenteeism anomaly reports
- Payroll distribution and salary summaries
- Recruitment funnel and time-to-fill metrics

### 📧 HR Communications
- Draft personalized employee notifications (leave warnings, payroll updates, onboarding messages)
- All emails require human approval before being sent

> **Note:** All create, update, and submit operations require human-in-the-loop approval before any change is written to Frappe.
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
        hooks=[HRAgentGovernanceHook()],
    )
