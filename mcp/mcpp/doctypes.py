"""Complete registry of Frappe HRMS DocTypes categorized by domain.

This registry provides agents with canonical DocType names, categorization,
and semantic descriptions without trial and error.
"""

from __future__ import annotations

from typing import TypedDict


class DocTypeMeta(TypedDict):
    category: str
    description: str
    submittable: bool


HR_DOCTYPES: dict[str, DocTypeMeta] = {
    # --- Core HR & Organizational Structure ---
    "Employee": {
        "category": "Core HR",
        "description": "Employee master record — personal, employment, and job details.",
        "submittable": False,
    },
    "Department": {
        "category": "Core HR",
        "description": "Organizational department or team hierarchy.",
        "submittable": False,
    },
    "Designation": {
        "category": "Core HR",
        "description": "Job title or role designation.",
        "submittable": False,
    },
    "Employee Grade": {
        "category": "Core HR",
        "description": "Seniority or pay grade level.",
        "submittable": False,
    },
    "Branch": {
        "category": "Core HR",
        "description": "Company branch or office location.",
        "submittable": False,
    },
    "Employee Group": {
        "category": "Core HR",
        "description": "Named group of employees for announcements or permissions.",
        "submittable": False,
    },
    "Employment Type": {
        "category": "Core HR",
        "description": "Full-time, Part-time, Contract, Intern.",
        "submittable": False,
    },

    # --- Attendance & Shifts ---
    "Attendance": {
        "category": "Attendance & Shifts",
        "description": "Daily attendance record (Present, Absent, Half Day, On Leave).",
        "submittable": True,
    },
    "Attendance Request": {
        "category": "Attendance & Shifts",
        "description": "Employee regularization request for missed punches or attendance.",
        "submittable": True,
    },
    "Shift Type": {
        "category": "Attendance & Shifts",
        "description": "Work shift schedule definitions (start/end times, thresholds).",
        "submittable": False,
    },
    "Shift Assignment": {
        "category": "Attendance & Shifts",
        "description": "Assigns an employee to a shift schedule for a date range.",
        "submittable": True,
    },
    "Shift Request": {
        "category": "Attendance & Shifts",
        "description": "Employee request to switch or take a different shift.",
        "submittable": True,
    },
    "Employee Checkin": {
        "category": "Attendance & Shifts",
        "description": "Raw biometric or app IN/OUT punch log.",
        "submittable": False,
    },

    # --- Leave & Holidays ---
    "Leave Application": {
        "category": "Leave Management",
        "description": "Employee request for time off with approval workflow.",
        "submittable": True,
    },
    "Leave Allocation": {
        "category": "Leave Management",
        "description": "Allocated days of leave for an employee for a period.",
        "submittable": True,
    },
    "Leave Type": {
        "category": "Leave Management",
        "description": "Leave master (Casual, Sick, Privilege) with carry-forward & earned rules.",
        "submittable": False,
    },
    "Leave Policy": {
        "category": "Leave Management",
        "description": "Package of leave allocations assigned across grades or departments.",
        "submittable": False,
    },
    "Leave Policy Assignment": {
        "category": "Leave Management",
        "description": "Assigns a Leave Policy to an employee.",
        "submittable": True,
    },
    "Leave Period": {
        "category": "Leave Management",
        "description": "Fiscal cycle / year for leave accounting.",
        "submittable": False,
    },
    "Holiday List": {
        "category": "Leave Management",
        "description": "Calendar of official company and regional holidays.",
        "submittable": False,
    },
    "Compensatory Leave Request": {
        "category": "Leave Management",
        "description": "Claim comp-off leave for working on holidays or weekends.",
        "submittable": True,
    },
    "Leave Encashment": {
        "category": "Leave Management",
        "description": "Encash unused earned leave balance into payroll payout.",
        "submittable": True,
    },

    # --- Payroll & Compensation ---
    "Salary Slip": {
        "category": "Payroll",
        "description": "Generated employee payslip for a payroll cycle.",
        "submittable": True,
    },
    "Salary Structure": {
        "category": "Payroll",
        "description": "Template defining earnings, deductions, and formulas.",
        "submittable": True,
    },
    "Salary Structure Assignment": {
        "category": "Payroll",
        "description": "Assigns a salary structure and base compensation to an employee.",
        "submittable": True,
    },
    "Salary Component": {
        "category": "Payroll",
        "description": "Component of salary (Basic, HRA, Provident Fund, Tax).",
        "submittable": False,
    },
    "Payroll Entry": {
        "category": "Payroll",
        "description": "Batch processing engine to generate monthly salary slips.",
        "submittable": True,
    },
    "Additional Salary": {
        "category": "Payroll",
        "description": "One-off bonus, deduction, or adjustment added to payroll.",
        "submittable": True,
    },
    "Employee Advance": {
        "category": "Payroll",
        "description": "Advance against upcoming salary payout.",
        "submittable": True,
    },
    "Loan": {
        "category": "Payroll",
        "description": "Company loan to an employee with EMI schedule.",
        "submittable": True,
    },
    "Income Tax Slab": {
        "category": "Payroll",
        "description": "Statutory income tax slabs and rates.",
        "submittable": False,
    },
    "Employee Benefit Claim": {
        "category": "Payroll",
        "description": "Flexible benefit reimbursement claim.",
        "submittable": True,
    },

    # --- Expenses & Travel ---
    "Expense Claim": {
        "category": "Expenses & Travel",
        "description": "Employee reimbursement claim for business expenses.",
        "submittable": True,
    },
    "Expense Claim Type": {
        "category": "Expenses & Travel",
        "description": "Classification for expenses (Travel, Client Lunch, Software).",
        "submittable": False,
    },
    "Travel Request": {
        "category": "Expenses & Travel",
        "description": "Business travel pre-authorization request.",
        "submittable": True,
    },

    # --- Recruitment ---
    "Job Opening": {
        "category": "Recruitment",
        "description": "Vacant position open for hiring.",
        "submittable": False,
    },
    "Job Applicant": {
        "category": "Recruitment",
        "description": "Candidate applicant record with resume and interview status.",
        "submittable": False,
    },
    "Job Offer": {
        "category": "Recruitment",
        "description": "Offer letter terms extended to a selected candidate.",
        "submittable": True,
    },
    "Interview": {
        "category": "Recruitment",
        "description": "Interview session scheduled for a candidate.",
        "submittable": True,
    },
    "Interview Round": {
        "category": "Recruitment",
        "description": "Interview stage definition (e.g. Tech Round, HR Round).",
        "submittable": False,
    },
    "Interview Feedback": {
        "category": "Recruitment",
        "description": "Interviewer scorecard and hiring recommendation.",
        "submittable": True,
    },
    "Staffing Plan": {
        "category": "Recruitment",
        "description": "Headcount target and hiring budget by department.",
        "submittable": True,
    },

    # --- Onboarding & Offboarding ---
    "Employee Onboarding": {
        "category": "Lifecycle",
        "description": "Checklist and task tracking for newly joined employees.",
        "submittable": True,
    },
    "Employee Separation": {
        "category": "Lifecycle",
        "description": "Resignation and offboarding workflow.",
        "submittable": True,
    },
    "Exit Interview": {
        "category": "Lifecycle",
        "description": "Exit interview feedback and questionnaire.",
        "submittable": False,
    },
    "Employee Transfer": {
        "category": "Lifecycle",
        "description": "Internal transfer to new department, designation, or branch.",
        "submittable": True,
    },
    "Employee Promotion": {
        "category": "Lifecycle",
        "description": "Promotion record updating role, grade, and salary.",
        "submittable": True,
    },

    # --- Performance & Training ---
    "Appraisal": {
        "category": "Performance",
        "description": "Annual/quarterly performance review document.",
        "submittable": True,
    },
    "Appraisal Cycle": {
        "category": "Performance",
        "description": "Performance review cycle definition.",
        "submittable": False,
    },
    "Appraisal Template": {
        "category": "Performance",
        "description": "KRA and KPI template criteria for appraisals.",
        "submittable": False,
    },
    "Goal": {
        "category": "Performance",
        "description": "Individual or organizational goal / OKR.",
        "submittable": False,
    },
    "Training Program": {
        "category": "Training",
        "description": "Curriculum for employee training courses.",
        "submittable": False,
    },
    "Training Event": {
        "category": "Training",
        "description": "Scheduled training workshop or event.",
        "submittable": True,
    },
    "Training Result": {
        "category": "Training",
        "description": "Employee score and completion certificate tracking.",
        "submittable": True,
    },
}


def format_registry_markdown(category_filter: str | None = None) -> str:
    """Format HR DocTypes into clean Markdown for LLM discovery."""
    categories: dict[str, list[tuple[str, DocTypeMeta]]] = {}
    for name, meta in sorted(HR_DOCTYPES.items()):
        cat = meta["category"]
        if category_filter and category_filter.lower() not in cat.lower():
            continue
        categories.setdefault(cat, []).append((name, meta))

    if not categories:
        return f"No HR DocTypes found matching category '{category_filter}'."

    lines = ["# Frappe HRMS DocTypes Registry\n"]
    for cat, items in categories.items():
        lines.append(f"### {cat}")
        for name, meta in items:
            sub = " *(Submittable)*" if meta["submittable"] else ""
            lines.append(f"- **`{name}`**{sub}: {meta['description']}")
        lines.append("")
    return "\n".join(lines)
