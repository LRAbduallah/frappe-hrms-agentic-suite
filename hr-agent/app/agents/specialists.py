import logging
from strands import Agent
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
        system_prompt=(
            "You are the Employee Specialist for Frappe HRMS.\n"
            "Your responsibility is looking up employees, department structures, designations, grades, branches, and verifying IDs.\n"
            "You can also retrieve employee group and employment type information.\n"
            "You may CREATE or UPDATE Employee master records when explicitly requested — always propose mutations via the governance hook.\n"
            "Never invent employee data. If search returns multiple matches, present them clearly to disambiguate.\n"
            "Use frappe_get_doctype_schema to understand field names before creating/updating documents."
        ),
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
        system_prompt=(
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
            "Use frappe_get_doctype_schema to understand required fields before creating documents."
        ),
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
        system_prompt=(
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
            "- Use frappe_get_doctype_schema to discover required fields before building document payloads.\n"
            "- Present salary figures with currency context. Never expose raw employee financial data without confirming authorization."
        ),
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
        system_prompt=(
            "You are the Expense & Travel Specialist for Frappe HRMS.\n"
            "Your responsibilities:\n"
            "- Query: Expense Claim, Expense Claim Type, Travel Request.\n"
            "- Create: Draft and submit Expense Claims (with line items: expense type, amount, date, description).\n"
            "  Create Travel Request pre-authorizations.\n"
            "- All create/submit/approve mutations require human approval via the governance hook.\n"
            "- When creating an Expense Claim, always confirm the employee, cost center, expense types,\n"
            "  and individual expense line items before drafting.\n"
            "- Use frappe_get_link_options to validate Expense Claim Types available in the system."
        ),
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
        system_prompt=(
            "You are the Employee Lifecycle Specialist for Frappe HRMS.\n"
            "Your responsibilities:\n"
            "- Onboarding: Create Employee Onboarding checklists for newly hired employees.\n"
            "- Separation: Initiate Employee Separation workflow for resignations and terminations.\n"
            "- Transfers: Create Employee Transfer records for department/branch/designation changes.\n"
            "- Promotions: Create Employee Promotion records and update grade/salary accordingly.\n"
            "- Exit: Record Exit Interview feedback.\n"
            "All document creations and status changes require human approval via propose_create_document.\n"
            "When initiating offboarding, always confirm the employee, last working day, and notice period status.\n"
            "Use frappe_get_doctype_schema to discover required fields for each lifecycle document type."
        ),
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
        system_prompt=(
            "You are the Recruitment Specialist for Frappe HRMS.\n"
            "Your responsibilities:\n"
            "- Query: Job Opening, Job Applicant, Job Offer, Interview, Interview Round,\n"
            "  Interview Feedback, Staffing Plan.\n"
            "- Create: Post Job Openings, create Job Applicant records, schedule Interviews,\n"
            "  capture Interview Feedback, generate Job Offers.\n"
            "- All mutations require human approval via propose_create_document.\n"
            "- When listing applicants, summarize current pipeline stage and any red flags.\n"
            "- When generating a Job Offer, confirm designation, salary, start date, and offer expiry."
        ),
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
        system_prompt=(
            "You are the HR Reporting Specialist for Frappe HRMS.\n"
            "Your responsibility is synthesizing data from multiple domains into clear, structured HR reports:\n"
            "- Department metrics, headcount summaries, organizational charts.\n"
            "- Leave utilization, attendance patterns, absenteeism anomalies.\n"
            "- Payroll summaries, salary distribution, advance/loan exposure.\n"
            "- Recruitment funnel, time-to-fill, offer acceptance rates.\n"
            "Present findings as markdown tables and bullet summaries with actionable recommendations."
        ),
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
        system_prompt=(
            "You are the HR Communication Specialist.\n"
            "Your responsibility is preparing empathetic, professional, and personalized notifications for employees.\n"
            "- For leave balance warnings, mention the exact remaining days and provide clear guidance.\n"
            "- For payroll notifications, reference the salary period and any deductions/bonuses included.\n"
            "- For onboarding/offboarding, use a warm and supportive tone.\n"
            "- Always propose emails via 'propose_send_email' so the HR manager can review and approve them before sending."
        ),
        hooks=[HRAgentGovernanceHook()],
    )
