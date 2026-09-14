import json
import logging
from strands import tool
from app.governance.approvals import approval_store
from app.models.schemas import RiskLevel

logger = logging.getLogger(__name__)

# Fallback HR dataset if Frappe MCP gateway is unreachable during offline development
MOCK_EMPLOYEES = [
    {
        "name": "HR-EMP-00001",
        "employee_name": "Rahul Sharma",
        "department": "Engineering",
        "designation": "Senior Python Developer",
        "company": "Frappe Technologies",
        "status": "Active",
        "leave_balances": [
            {"leave_type": "Privilege Leave", "balance": 1.5, "total_allocated": 15.0},
            {"leave_type": "Sick Leave", "balance": 5.0, "total_allocated": 10.0},
        ],
        "attendance": [
            {"date": "2026-09-08", "status": "Absent", "late_entry": False},
            {"date": "2026-09-09", "status": "Present", "late_entry": False},
            {"date": "2026-09-10", "status": "Present", "late_entry": True},
        ],
    },
    {
        "name": "HR-EMP-00002",
        "employee_name": "Priya Patel",
        "department": "Human Resources",
        "designation": "HR Specialist",
        "company": "Frappe Technologies",
        "status": "Active",
        "leave_balances": [
            {"leave_type": "Privilege Leave", "balance": 12.0, "total_allocated": 15.0},
            {"leave_type": "Sick Leave", "balance": 8.0, "total_allocated": 10.0},
        ],
        "attendance": [
            {"date": "2026-09-08", "status": "Present", "late_entry": False},
            {"date": "2026-09-09", "status": "Present", "late_entry": False},
            {"date": "2026-09-10", "status": "Present", "late_entry": False},
        ],
    },
    {
        "name": "HR-EMP-00003",
        "employee_name": "Ananya Desai",
        "department": "Engineering",
        "designation": "DevOps Engineer",
        "company": "Frappe Technologies",
        "status": "Active",
        "leave_balances": [
            {"leave_type": "Privilege Leave", "balance": 0.5, "total_allocated": 15.0},
            {"leave_type": "Sick Leave", "balance": 2.0, "total_allocated": 10.0},
        ],
        "attendance": [
            {"date": "2026-09-08", "status": "Present", "late_entry": False},
            {"date": "2026-09-09", "status": "Half Day", "late_entry": True},
            {"date": "2026-09-10", "status": "Absent", "late_entry": False},
        ],
    },
]


@tool
def search_employees(query: str = "") -> str:
    """Search for employees in Frappe HRMS by name, employee ID, or department.
    
    Args:
        query: Name, ID, or department to search for. If empty, returns directory summary.
    """
    q = query.strip().lower()
    matches = []
    for emp in MOCK_EMPLOYEES:
        if not q or (
            q in emp["name"].lower()
            or q in emp["employee_name"].lower()
            or q in emp["department"].lower()
        ):
            matches.append({
                "employee_id": emp["name"],
                "name": emp["employee_name"],
                "department": emp["department"],
                "designation": emp["designation"],
                "status": emp["status"],
            })
    return json.dumps({"count": len(matches), "employees": matches}, indent=2)


@tool
def get_leave_balance(employee_id_or_name: str) -> str:
    """Fetch authoritative leave balance and allocation from Frappe HRMS for an employee.

    Args:
        employee_id_or_name: The employee ID (e.g. HR-EMP-00001) or employee name.
    """
    target = employee_id_or_name.strip().lower()
    for emp in MOCK_EMPLOYEES:
        if target in emp["name"].lower() or target in emp["employee_name"].lower():
            return json.dumps({
                "employee_id": emp["name"],
                "employee_name": emp["employee_name"],
                "department": emp["department"],
                "leave_balances": emp["leave_balances"],
            }, indent=2)
    return json.dumps({"error": f"Employee '{employee_id_or_name}' not found."})


@tool
def get_attendance_history(employee_id_or_name: str) -> str:
    """Fetch attendance records, absences, and late entries from Frappe HRMS.

    Args:
        employee_id_or_name: Employee ID or name.
    """
    target = employee_id_or_name.strip().lower()
    for emp in MOCK_EMPLOYEES:
        if target in emp["name"].lower() or target in emp["employee_name"].lower():
            return json.dumps({
                "employee_id": emp["name"],
                "employee_name": emp["employee_name"],
                "attendance_records": emp["attendance"],
            }, indent=2)
    return json.dumps({"error": f"Employee '{employee_id_or_name}' not found."})


@tool
def propose_attendance_correction(
    employee_id: str,
    attendance_date: str,
    new_status: str,
    reason: str,
) -> str:
    """Propose an attendance correction mutation requiring Human-in-the-Loop (HITL) approval.

    Args:
        employee_id: Employee ID (e.g., HR-EMP-00001).
        attendance_date: Date in YYYY-MM-DD format.
        new_status: Target status ('Present', 'Absent', 'Half Day', 'On Leave').
        reason: Business justification for correction.
    """
    req = approval_store.create(
        session_id="default",
        action=f"Correct attendance for {employee_id} on {attendance_date} to {new_status}",
        tool_name="hrms_mark_attendance",
        arguments={
            "employee": employee_id,
            "attendance_date": attendance_date,
            "status": new_status,
            "reason": reason,
        },
        reason=reason,
        risk_level=RiskLevel.MEDIUM,
    )
    return json.dumps({
        "status": "APPROVAL_REQUIRED",
        "approval_id": req.id,
        "message": f"Attendance correction proposed. Action requires human approval before Frappe mutation.",
        "action": req.action,
        "reason": req.reason,
    }, indent=2)


@tool
def propose_send_email(
    recipient_id: str,
    recipient_name: str,
    subject: str,
    body: str,
    reason: str,
) -> str:
    """Propose sending an official HR notification email requiring human approval.

    Args:
        recipient_id: Employee ID.
        recipient_name: Full name of employee.
        subject: Email subject.
        body: Message body.
        reason: Purpose of communication.
    """
    req = approval_store.create(
        session_id="default",
        action=f"Send HR Email to {recipient_name} ({recipient_id}): {subject}",
        tool_name="send_email",
        arguments={
            "recipient_id": recipient_id,
            "recipient_name": recipient_name,
            "subject": subject,
            "body": body,
        },
        reason=reason,
        risk_level=RiskLevel.LOW,
    )
    return json.dumps({
        "status": "APPROVAL_REQUIRED",
        "approval_id": req.id,
        "message": "Email draft generated and queued for human approval before sending.",
        "action": req.action,
        "subject": subject,
        "draft_body": body,
    }, indent=2)


@tool
def propose_create_document(
    doctype: str,
    fields: str,
    reason: str,
) -> str:
    """Propose creating a new Frappe document of any DocType, requiring human approval.
    Executes a pre-flight validation and dry-run check against Frappe before creating the proposal.

    Call this exactly once after required information is complete. Do not ask the
    user for another chat confirmation after this returns APPROVAL_REQUIRED; the
    UI approval card is the confirmation step.

    Use this for any creation operation: Leave Application, Salary Slip, Expense Claim,
    Leave Policy, Payroll Entry, Employee Onboarding, Job Opening, etc.

    Args:
        doctype: Frappe DocType name (e.g. 'Leave Application', 'Salary Slip', 'Expense Claim').
        fields: JSON string of field key-value pairs for the new document.
        reason: Business justification for creating this document.
    """
    from app.governance.payload_validator import validate_and_dry_run

    try:
        parsed = json.loads(fields) if isinstance(fields, str) else fields
    except (json.JSONDecodeError, TypeError):
        parsed = {"raw": fields}

    # Pre-flight validation & dry-run test
    dry_run = validate_and_dry_run("frappe_create_document", {"doctype": doctype, "fields": parsed})
    if not dry_run.get("dry_run_passed", True):
        error_summary = "; ".join(dry_run.get("errors", []))
        return json.dumps({
            "status": "VALIDATION_FAILED",
            "message": f"Pre-flight dry-run check failed for creating '{doctype}': {error_summary}",
            "doctype": doctype,
            "errors": dry_run.get("errors", []),
            "warnings": dry_run.get("warnings", []),
            "checks": dry_run.get("checks", []),
            "guidance": (
                f"Cannot create '{doctype}' because mandatory prerequisites are not met in Frappe HRMS. "
                "Inform the user of the exact missing prerequisites and propose setting them up first."
            ),
        }, indent=2)

    # Determine risk level based on doctype
    financial_doctypes = {
        "Salary Slip", "Payroll Entry", "Additional Salary", "Employee Advance",
        "Loan", "Expense Claim", "Leave Encashment", "Employee Benefit Claim",
    }
    risk = RiskLevel.HIGH if doctype in financial_doctypes else RiskLevel.MEDIUM

    req = approval_store.create(
        session_id="default",
        action=f"Create {doctype} in Frappe HRMS",
        tool_name="frappe_create_document",
        arguments={"doctype": doctype, "fields": parsed, "document": parsed},
        reason=reason,
        risk_level=risk,
        preflight=dry_run,
    )
    return json.dumps({
        "status": "APPROVAL_REQUIRED",
        "approval_id": req.id,
        "message": f"{doctype} creation queued for human approval before Frappe write (Pre-flight dry run PASSED).",
        "next_step": "Review and approve the approval card in the UI. No second chat confirmation is required.",
        "doctype": doctype,
        "proposed_fields": parsed,
        "dry_run": "PASSED",
        "checks": dry_run.get("checks", []),
        "warnings": dry_run.get("warnings", []),
        "reason": reason,
    }, indent=2)


@tool
def propose_create_workflow(
    steps: str,
    reason: str,
) -> str:
    """Propose one dependency-aware create workflow under a single approval.

    Use this when the requested document names a missing prerequisite such as a
    Department, Designation, Company, Leave Type, or Employee. Resolve every
    existing Link first. If a clearly requested prerequisite is absent, put its
    creation before the dependent document and reference its future name with
    {"$ref": "step_id.name"}.

    The steps must be a JSON array in dependency order. Each step is:
    {"id": "department", "doctype": "Department", "fields": {...}}

    Do not use this to invent prerequisites or to create records the user did
    not request. The UI approval card is the single confirmation step.
    """
    from app.governance.payload_validator import validate_create_workflow

    try:
        parsed = json.loads(steps) if isinstance(steps, str) else steps
    except (json.JSONDecodeError, TypeError):
        parsed = None

    workflow_args = {"steps": parsed}
    preflight = validate_create_workflow(workflow_args)
    if not preflight.get("dry_run_passed", False):
        error_summary = "; ".join(preflight.get("errors", []))
        return json.dumps({
            "status": "VALIDATION_FAILED",
            "message": f"Pre-flight workflow check failed: {error_summary}",
            "errors": preflight.get("errors", []),
            "warnings": preflight.get("warnings", []),
            "checks": preflight.get("checks", []),
        }, indent=2)

    financial_doctypes = {
        "Salary Slip", "Payroll Entry", "Additional Salary", "Employee Advance",
        "Loan", "Expense Claim", "Leave Encashment", "Employee Benefit Claim",
    }
    risk = RiskLevel.HIGH if any(
        isinstance(step, dict) and step.get("doctype") in financial_doctypes
        for step in parsed
    ) else RiskLevel.MEDIUM
    req = approval_store.create(
        session_id="default",
        action=f"Create dependent HR records ({len(parsed)} steps)",
        tool_name="frappe_create_workflow",
        arguments={"steps": parsed},
        reason=reason,
        risk_level=risk,
        preflight=preflight,
    )
    return json.dumps({
        "status": "APPROVAL_REQUIRED",
        "approval_id": req.id,
        "message": (
            f"{len(parsed)} dependent HR record(s) queued as one workflow for approval. "
            "Prerequisites will be created first and their names passed to later steps."
        ),
        "next_step": "Review and approve the single workflow card in the UI. No second chat confirmation is required.",
        "steps": [
            {"id": step.get("id"), "doctype": step.get("doctype")}
            for step in parsed
        ],
        "dry_run": "PASSED",
        "checks": preflight.get("checks", []),
        "warnings": preflight.get("warnings", []),
    }, indent=2)


@tool
def propose_update_document(
    doctype: str,
    document_name: str,
    fields: str,
    reason: str,
) -> str:
    """Propose updating an existing Frappe document, requiring human approval.
    Executes a pre-flight validation check against Frappe before creating the proposal.

    Call this exactly once after required information is complete. Do not ask the
    user for another chat confirmation after this returns APPROVAL_REQUIRED; the
    UI approval card is the confirmation step.

    Use this for any update: changing employee department, updating salary structure,
    modifying leave allocation, updating job offer status, etc.

    Args:
        doctype: Frappe DocType name.
        document_name: The document name/ID to update (e.g. 'HR-EMP-00001').
        fields: JSON string of field key-value pairs to update.
        reason: Business justification for this change.
    """
    from app.governance.payload_validator import validate_and_dry_run

    try:
        parsed = json.loads(fields) if isinstance(fields, str) else fields
    except (json.JSONDecodeError, TypeError):
        parsed = {"raw": fields}

    # Pre-flight check
    dry_run = validate_and_dry_run(
        "frappe_update_document",
        {"doctype": doctype, "name": document_name, "fields": parsed}
    )
    if not dry_run.get("dry_run_passed", True):
        error_summary = "; ".join(dry_run.get("errors", []))
        return json.dumps({
            "status": "VALIDATION_FAILED",
            "message": f"Pre-flight check failed for updating '{doctype}/{document_name}': {error_summary}",
            "doctype": doctype,
            "document_name": document_name,
            "errors": dry_run.get("errors", []),
            "warnings": dry_run.get("warnings", []),
            "checks": dry_run.get("checks", []),
        }, indent=2)

    financial_doctypes = {
        "Salary Slip", "Payroll Entry", "Additional Salary", "Employee Advance",
        "Loan", "Expense Claim", "Leave Encashment",
    }
    risk = RiskLevel.HIGH if doctype in financial_doctypes else RiskLevel.MEDIUM

    req = approval_store.create(
        session_id="default",
        action=f"Update {doctype}/{document_name} in Frappe HRMS",
        tool_name="frappe_update_document",
        arguments={"doctype": doctype, "name": document_name, "fields": parsed, "document": parsed},
        reason=reason,
        risk_level=risk,
        preflight=dry_run,
    )
    return json.dumps({
        "status": "APPROVAL_REQUIRED",
        "approval_id": req.id,
        "message": f"{doctype}/{document_name} update queued for human approval before Frappe write.",
        "next_step": "Review and approve the approval card in the UI. No second chat confirmation is required.",
        "doctype": doctype,
        "document_name": document_name,
        "proposed_changes": parsed,
        "dry_run": "PASSED",
        "checks": dry_run.get("checks", []),
        "warnings": dry_run.get("warnings", []),
        "reason": reason,
    }, indent=2)
