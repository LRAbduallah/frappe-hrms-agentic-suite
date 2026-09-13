import logging
from strands import Agent
from app.agents.context import conversation_manager
from app.hooks.governance import HRAgentGovernanceHook
from app.mcp.manager import mcp_manager
from app.models.llm import get_model
from app.tools.hr_tools import (
    search_employees,
    get_leave_balance,
    get_attendance_history,
    propose_attendance_correction,
    propose_send_email,
    propose_create_document,
    propose_update_document,
)

logger = logging.getLogger(__name__)

SPECIALIST_INTERACTION_POLICY = (
    "\n\nInteraction policy:\n"
    "- Behave like a patient HR colleague helping a non-technical user.\n"
    "- First inspect the live creation plan, then reuse user-provided values and safe live defaults.\n"
    "- Ask at most one grouped clarification question containing only missing mandatory details or "
    "ambiguous Link choices. Do not ask one question per field.\n"
    "- Auto-select a Link only when the live lookup returns exactly one valid record; ask the user when "
    "there are multiple records, and never invent one.\n"
    "- Do not ask for optional fields unless they materially affect the requested action.\n"
    "- Do not ask 'shall I proceed?' repeatedly. After the payload passes preflight, call the proposal "
    "tool once; the UI approval card is the only confirmation step.\n"
    "- If preflight fails, explain the exact failure, ask only for the corrective values, and do not retry "
    "the same payload blindly.\n"
)


def _specialist_prompt(body: str) -> str:
    return body + SPECIALIST_INTERACTION_POLICY


# ─── Employee & Directory ──────────────────────────────────────────────────────

def create_employee_agent() -> Agent:
    """Specialist: employee identity, directory, department, profiles, org chart."""
    model = get_model()
    mcp_tools = mcp_manager.get_tools_for_employee_agent()
    approval_tools = [propose_create_document, propose_update_document]
    tools = mcp_tools + approval_tools if mcp_tools else [search_employees] + approval_tools

    return Agent(
        name="employee_agent",
        model=model,
        tools=tools,
        system_prompt=_specialist_prompt(
            "You are the Employee Specialist for Frappe HRMS.\n"
            "Your responsibility is looking up employees, department structures, designations, grades, branches, and verifying IDs.\n"
            "You can also retrieve employee group and employment type information.\n"
            "You may CREATE or UPDATE Employee master records when explicitly requested — always propose mutations via the governance hook.\n"
            "Never invent employee data. If search returns multiple matches, present them clearly to disambiguate.\n"
            "Before creating/updating, call frappe_get_creation_plan and use only its live field names and Link options. "
            "Ask the user to choose when multiple companies, departments, or other linked records exist. "
            "Call frappe_get_api_catalog only if the relationship map is unknown. Keep tool results out of the user answer."
        ),
        conversation_manager=conversation_manager(specialist=True),
        hooks=[HRAgentGovernanceHook()],
    )


# ─── Leave & Attendance ────────────────────────────────────────────────────────

def create_leave_attendance_agent() -> Agent:
    """Specialist: leave allocations, balances, policies, attendance, shifts, corrections."""
    model = get_model()
    mcp_tools = mcp_manager.get_tools_for_leave_agent()
    approval_tools = [propose_attendance_correction, propose_create_document, propose_update_document]
    base_tools = [
        get_leave_balance,
        get_attendance_history,
        search_employees,
    ]
    tools = mcp_tools + approval_tools if mcp_tools else base_tools + approval_tools

    return Agent(
        name="leave_attendance_agent",
        model=model,
        tools=tools,
        system_prompt=_specialist_prompt(
            "You are the Leave & Attendance Specialist for Frappe HRMS.\n"
            "Your responsibilities:\n"
            "- Leave queries: balances, allocations, leave types, leave periods, holiday lists.\n"
            "- Leave actions: create Leave Application, Leave Allocation, Leave Policy, Leave Policy Assignment,\n"
            "  Compensatory Leave Request, Leave Encashment — always route mutations through propose_create_document.\n"
            "- Attendance queries: daily attendance, employee check-in/out logs, shift assignments.\n"
            "- Attendance actions: correct attendance records, mark attendance — use propose_attendance_correction\n"
            "  so human approval is required before applying changes to Frappe.\n"
            "- Shift actions: create Shift Assignment, Shift Request.\n"
            "- Critically low leave is defined as <= 2.0 days remaining.\n"
            "Always retrieve authoritative facts from Frappe before making recommendations.\n"
            "Before creating, call frappe_get_creation_plan to resolve required fields, prerequisites, and real Link options. "
            "Never choose the first Company, Employee, Leave Type, or other linked record silently. "
            "Prefer filtered lookups over dumping option lists."
        ),
        conversation_manager=conversation_manager(specialist=True),
        hooks=[HRAgentGovernanceHook()],
    )


# ─── Payroll & Compensation ────────────────────────────────────────────────────

def create_payroll_agent() -> Agent:
    """Specialist: salary slips, payroll entries, salary structures, components, advances, loans."""
    model = get_model()
    mcp_tools = mcp_manager.get_tools_for_payroll_agent()
    approval_tools = [propose_create_document, propose_update_document]
    base_tools = [search_employees, get_leave_balance]
    tools = mcp_tools + approval_tools if mcp_tools else base_tools + approval_tools

    return Agent(
        name="payroll_agent",
        model=model,
        tools=tools,
        system_prompt=_specialist_prompt(
            "You are the Payroll & Compensation Specialist for Frappe HRMS.\n"
            "Your responsibilities:\n"
            "- Query: Salary Slip, Salary Structure, Salary Structure Assignment, Salary Component,\n"
            "  Payroll Entry, Additional Salary, Employee Advance, Loan, Income Tax Slab, Employee Benefit Claim.\n"
            "- Create/Process: Generate salary slips for an employee or batch via Payroll Entry.\n"
            "  Create Salary Structure, Salary Structure Assignment, Additional Salary (bonus/deduction), Employee Advance.\n"
            "- All mutations (create, submit, cancel) MUST be proposed via propose_create_document or propose_update_document\n"
            "  so human approval gates the actual Frappe write.\n"
            "- IMPORTANT: Every proposed document runs an automatic pre-flight dry-run check against Frappe.\n"
            "  Before proposing a Salary Slip, ensure the employee has an active Salary Structure Assignment\n"
            "  and that a Holiday List exists in Frappe. If propose_create_document returns VALIDATION_FAILED,\n"
            "  inform the user clearly of what prerequisites are missing rather than retrying blindly.\n"
            "- When asked to 'run payroll' for a period, clarify the company, payroll frequency, and date range first.\n"
            "- Use frappe_get_creation_plan to discover required fields, prerequisites, child tables, and real Link values before building payloads.\n"
            "- Present salary figures with currency context. Never expose raw employee financial data without confirming authorization. "
            "Keep MCP results compact and out of the user-facing answer."
        ),
        conversation_manager=conversation_manager(specialist=True),
        hooks=[HRAgentGovernanceHook()],
    )


# ─── Expenses & Travel ─────────────────────────────────────────────────────────

def create_expense_agent() -> Agent:
    """Specialist: expense claims, travel requests, reimbursements."""
    model = get_model()
    mcp_tools = mcp_manager.get_tools_for_expense_agent()
    approval_tools = [propose_create_document, propose_update_document]
    base_tools = [search_employees]
    tools = mcp_tools + approval_tools if mcp_tools else base_tools + approval_tools

    return Agent(
        name="expense_agent",
        model=model,
        tools=tools,
        system_prompt=_specialist_prompt(
            "You are the Expense & Travel Specialist for Frappe HRMS.\n"
            "Your responsibilities:\n"
            "- Query: Expense Claim, Expense Claim Type, Travel Request.\n"
            "- Create: Draft and submit Expense Claims (with line items: expense type, amount, date, description).\n"
            "  Create Travel Request pre-authorizations.\n"
            "- All create/submit/approve mutations require human approval via the governance hook.\n"
            "- When creating an Expense Claim, confirm the employee, cost center, expense types,\n"
            "  and individual expense line items only when they are missing or ambiguous.\n"
            "- Use frappe_get_creation_plan and frappe_get_link_options to validate every Expense Claim link and ask the user to choose among multiple valid records."
        ),
        conversation_manager=conversation_manager(specialist=True),
        hooks=[HRAgentGovernanceHook()],
    )


# ─── Employee Lifecycle ─────────────────────────────────────────────────────────

def create_lifecycle_agent() -> Agent:
    """Specialist: onboarding, separation, transfer, promotion, exit interviews."""
    model = get_model()
    mcp_tools = mcp_manager.get_tools_for_lifecycle_agent()
    approval_tools = [propose_create_document, propose_update_document]
    base_tools = [search_employees]
    tools = mcp_tools + approval_tools if mcp_tools else base_tools + approval_tools

    return Agent(
        name="lifecycle_agent",
        model=model,
        tools=tools,
        system_prompt=_specialist_prompt(
            "You are the Employee Lifecycle Specialist for Frappe HRMS.\n"
            "Your responsibilities:\n"
            "- Onboarding: Create Employee Onboarding checklists for newly hired employees.\n"
            "- Separation: Initiate Employee Separation workflow for resignations and terminations.\n"
            "- Transfers: Create Employee Transfer records for department/branch/designation changes.\n"
            "- Promotions: Create Employee Promotion records and update grade/salary accordingly.\n"
            "- Exit: Record Exit Interview feedback.\n"
            "All document creations and status changes require human approval via propose_create_document.\n"
            "When initiating offboarding, confirm the employee, last working day, and notice period status only when missing or ambiguous.\n"
            "Use frappe_get_creation_plan to discover required fields, prerequisites, and valid links for each lifecycle document type. "
            "Ask the user to choose among multiple employees, companies, departments, or other links."
        ),
        conversation_manager=conversation_manager(specialist=True),
        hooks=[HRAgentGovernanceHook()],
    )


# ─── Recruitment ───────────────────────────────────────────────────────────────

def create_recruitment_agent() -> Agent:
    """Specialist: job openings, applicants, interviews, offers, staffing plans."""
    model = get_model()
    mcp_tools = mcp_manager.get_tools_for_recruitment_agent()
    approval_tools = [propose_create_document, propose_update_document]
    base_tools = [search_employees]
    tools = mcp_tools + approval_tools if mcp_tools else base_tools + approval_tools

    return Agent(
        name="recruitment_agent",
        model=model,
        tools=tools,
        system_prompt=_specialist_prompt(
            "You are the Recruitment Specialist for Frappe HRMS.\n"
            "Your responsibilities:\n"
            "- Query: Job Opening, Job Applicant, Job Offer, Interview, Interview Round,\n"
            "  Interview Feedback, Staffing Plan.\n"
            "- Create: Post Job Openings, create Job Applicant records, schedule Interviews,\n"
            "  capture Interview Feedback, generate Job Offers.\n"
            "- All mutations require human approval via propose_create_document.\n"
            "- When listing applicants, summarize current pipeline stage and any red flags.\n"
            "- When generating a Job Offer, confirm designation, salary, start date, and offer expiry only when missing or ambiguous.\n"
            "- Use frappe_get_creation_plan before every recruitment write and never invent Job Opening, Company, Applicant, or other Link values."
        ),
        conversation_manager=conversation_manager(specialist=True),
        hooks=[HRAgentGovernanceHook()],
    )


# ─── Reporting ─────────────────────────────────────────────────────────────────

def create_reporting_agent() -> Agent:
    """Specialist: organizational summaries, metrics, cross-domain HR reports."""
    model = get_model()
    mcp_tools = mcp_manager.get_tools_for_reporting_agent()
    base_tools = [search_employees, get_leave_balance, get_attendance_history]
    tools = mcp_tools if mcp_tools else base_tools

    return Agent(
        name="reporting_agent",
        model=model,
        tools=tools,
        system_prompt=_specialist_prompt(
            "You are the HR Reporting Specialist for Frappe HRMS.\n"
            "Your responsibility is synthesizing data from multiple domains into clear, structured HR reports:\n"
            "- Department metrics, headcount summaries, organizational charts.\n"
            "- Leave utilization, attendance patterns, absenteeism anomalies.\n"
            "- Payroll summaries, salary distribution, advance/loan exposure.\n"
            "- Recruitment funnel, time-to-fill, offer acceptance rates.\n"
            "Present findings as markdown tables and bullet summaries with actionable recommendations. "
            "Do not load API catalogs or full schemas for reporting queries."
        ),
        conversation_manager=conversation_manager(specialist=True),
        hooks=[HRAgentGovernanceHook()],
    )


# ─── Communication ─────────────────────────────────────────────────────────────

def create_communication_agent() -> Agent:
    """Specialist: drafting personalized HR communications and alerts."""
    model = get_model()
    tools = [propose_send_email, search_employees]

    return Agent(
        name="communication_agent",
        model=model,
        tools=tools,
        system_prompt=_specialist_prompt(
            "You are the HR Communication Specialist.\n"
            "Your responsibility is preparing empathetic, professional, and personalized notifications for employees.\n"
            "- For leave balance warnings, mention the exact remaining days and provide clear guidance.\n"
            "- For payroll notifications, reference the salary period and any deductions/bonuses included.\n"
            "- For onboarding/offboarding, use a warm and supportive tone.\n"
            "- Always propose emails via 'propose_send_email' so the HR manager can review and approve them before sending."
        ),
        conversation_manager=conversation_manager(specialist=True),
        hooks=[HRAgentGovernanceHook()],
    )
