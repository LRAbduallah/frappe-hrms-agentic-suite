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


class CreationGuidance(TypedDict):
    prerequisites: list[str]
    link_fields: dict[str, str]
    creation_notes: list[str]
    after_create: list[str]


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


# This is workflow guidance, not a substitute for live DocType metadata. The
# discovery tools always fetch the installed Frappe schema and current Link
# values before a write; this map tells the agent what it should verify first.
DOCTYPE_CREATION_GUIDANCE: dict[str, CreationGuidance] = {
    "Department": {
        "prerequisites": ["Company"],
        "link_fields": {"company": "Company", "parent_department": "Department"},
        "creation_notes": ["Use the exact company name already present in Frappe.", "Ask whether this is a child department before setting parent_department."],
        "after_create": [],
    },
    "Employee": {
        "prerequisites": ["Company", "Department", "Designation", "Employment Type", "Employee Group"],
        "link_fields": {
            "company": "Company",
            "department": "Department",
            "designation": "Designation",
            "branch": "Branch",
            "employment_type": "Employment Type",
            "employee_group": "Employee Group",
            "reports_to": "Employee",
        },
        "creation_notes": ["Never invent employee, company, department, designation, or branch names.", "Collect the employee's legal name, joining date, status, and contact details required by the live schema."],
        "after_create": [],
    },
    "Attendance": {
        "prerequisites": ["Employee", "Company"],
        "link_fields": {"employee": "Employee", "company": "Company", "shift": "Shift Type"},
        "creation_notes": ["Confirm the employee and attendance date before writing.", "Use only the allowed status values returned by the live schema."],
        "after_create": ["Submit if the installed DocType is submittable and the user requested a submitted record."],
    },
    "Leave Application": {
        "prerequisites": ["Employee", "Leave Type", "Leave Period", "Company", "Holiday List"],
        "link_fields": {"employee": "Employee", "leave_type": "Leave Type", "company": "Company", "leave_approver": "User"},
        "creation_notes": ["Verify the employee has available balance for the selected Leave Type.", "Confirm date range, half-day details, and approver when required by the live schema."],
        "after_create": ["Submit only after the user explicitly requests submission; creation alone leaves the application in draft."],
    },
    "Leave Allocation": {
        "prerequisites": ["Employee", "Leave Type", "Leave Period", "Company"],
        "link_fields": {"employee": "Employee", "leave_type": "Leave Type", "company": "Company"},
        "creation_notes": ["Confirm allocation dates and number of days.", "Do not assume the active Leave Period when more than one exists."],
        "after_create": ["Submit when the user requests the allocation to take effect."],
    },
    "Leave Policy Assignment": {
        "prerequisites": ["Employee", "Leave Policy", "Leave Period"],
        "link_fields": {"employee": "Employee", "leave_policy": "Leave Policy"},
        "creation_notes": ["Ask which policy and leave period should be assigned when multiple valid records exist."],
        "after_create": ["Submit when required by the installed workflow."],
    },
    "Holiday List": {
        "prerequisites": ["Company"],
        "link_fields": {"company": "Company"},
        "creation_notes": ["Confirm the country/region and calendar year before creating holidays.", "Child holiday rows must use valid dates."],
        "after_create": [],
    },
    "Salary Structure": {
        "prerequisites": ["Company", "Salary Component"],
        "link_fields": {"company": "Company"},
        "creation_notes": ["Resolve every earning and deduction component from Frappe before building child rows.", "Do not invent formulas or account names."],
        "after_create": ["Submit only after component rows and payroll settings are verified."],
    },
    "Salary Structure Assignment": {
        "prerequisites": ["Employee", "Salary Structure", "Company"],
        "link_fields": {"employee": "Employee", "salary_structure": "Salary Structure", "company": "Company"},
        "creation_notes": ["Confirm effective-from date, base, currency, and payroll frequency.", "Ask the user to choose when multiple active structures exist."],
        "after_create": ["Submit when required by the installed workflow."],
    },
    "Salary Slip": {
        "prerequisites": ["Employee", "Salary Structure Assignment", "Company", "Payroll Entry", "Holiday List"],
        "link_fields": {"employee": "Employee", "company": "Company", "payroll_entry": "Payroll Entry"},
        "creation_notes": ["Verify an active Salary Structure Assignment and payroll period before creation.", "Prefer Frappe's payroll generation workflow when available instead of hand-building earnings."],
        "after_create": ["Submit only after totals and deductions are reviewed and the user explicitly requests submission."],
    },
    "Payroll Entry": {
        "prerequisites": ["Company", "Payroll Period", "Currency", "Account"],
        "link_fields": {"company": "Company", "currency": "Currency"},
        "creation_notes": ["Confirm payroll dates, employees, currency, and posting accounts.", "Do not create payroll for an ambiguous period."],
        "after_create": ["Use the installed payroll workflow to fetch employees and create salary slips."],
    },
    "Expense Claim": {
        "prerequisites": ["Employee", "Company", "Expense Claim Type", "Currency", "Cost Center"],
        "link_fields": {"employee": "Employee", "company": "Company", "expense_type": "Expense Claim Type", "cost_center": "Cost Center"},
        "creation_notes": ["Collect expense dates, amounts, currencies, receipts, and expense line items.", "Resolve the employee's company and valid expense types from Frappe."],
        "after_create": ["Submit only after receipt and amount review."],
    },
    "Travel Request": {
        "prerequisites": ["Employee", "Company"],
        "link_fields": {"employee": "Employee", "company": "Company"},
        "creation_notes": ["Collect travel purpose, destinations, dates, and estimated costs.", "Ask for missing itinerary details instead of creating a partial request."],
        "after_create": ["Submit when the user explicitly requests approval workflow."],
    },
    "Job Opening": {
        "prerequisites": ["Company", "Department", "Designation"],
        "link_fields": {"company": "Company", "department": "Department", "designation": "Designation"},
        "creation_notes": ["Confirm role, department, designation, vacancies, and planned start date."],
        "after_create": [],
    },
    "Job Applicant": {
        "prerequisites": ["Job Opening"],
        "link_fields": {"job_title": "Job Opening"},
        "creation_notes": ["Collect applicant name and contact details; link to an existing Job Opening when applicable."],
        "after_create": [],
    },
    "Job Offer": {
        "prerequisites": ["Job Applicant", "Job Opening", "Company"],
        "link_fields": {"job_applicant": "Job Applicant", "job_opening": "Job Opening", "company": "Company"},
        "creation_notes": ["Confirm offered designation, compensation, currency, and validity dates."],
        "after_create": ["Submit only after offer terms are reviewed."],
    },
    "Employee Onboarding": {
        "prerequisites": ["Employee", "Company"],
        "link_fields": {"employee": "Employee", "company": "Company"},
        "creation_notes": ["Confirm joining date and onboarding activities from the installed schema."],
        "after_create": ["Submit when the onboarding workflow should begin."],
    },
    "Employee Separation": {
        "prerequisites": ["Employee", "Company"],
        "link_fields": {"employee": "Employee", "company": "Company"},
        "creation_notes": ["Confirm separation type, resignation/relieving dates, and exit reason."],
        "after_create": ["Submit only after the user confirms the effective separation action."],
    },
    "Employee Transfer": {
        "prerequisites": ["Employee", "Department", "Designation", "Branch", "Company"],
        "link_fields": {"employee": "Employee", "new_department": "Department", "new_designation": "Designation", "new_branch": "Branch", "company": "Company"},
        "creation_notes": ["Confirm effective date and every destination field; never infer a department from a name alone."],
        "after_create": ["Submit when the transfer should take effect."],
    },
    "Employee Promotion": {
        "prerequisites": ["Employee", "Designation", "Employee Grade", "Company"],
        "link_fields": {"employee": "Employee", "designation": "Designation", "grade": "Employee Grade", "company": "Company"},
        "creation_notes": ["Confirm effective date, new designation/grade, and compensation changes."],
        "after_create": ["Submit when the promotion should take effect."],
    },
    "Designation": {
        "prerequisites": [],
        "link_fields": {},
        "creation_notes": ["Use a unique, human-readable designation name."],
        "after_create": [],
    },
    "Employee Grade": {
        "prerequisites": [],
        "link_fields": {},
        "creation_notes": ["Confirm the grade name and any configured salary/rank conventions."],
        "after_create": [],
    },
    "Branch": {
        "prerequisites": ["Company"],
        "link_fields": {"company": "Company"},
        "creation_notes": ["Use an existing Company and a unique branch name."],
        "after_create": [],
    },
    "Employment Type": {
        "prerequisites": [],
        "link_fields": {},
        "creation_notes": ["Use a configured employment type such as Full-time, Part-time, Contract, or Intern when applicable."],
        "after_create": [],
    },
    "Employee Group": {
        "prerequisites": [],
        "link_fields": {},
        "creation_notes": ["Use a unique group name and confirm whether it is used for permissions or announcements."],
        "after_create": [],
    },
    "Shift Type": {
        "prerequisites": [],
        "link_fields": {},
        "creation_notes": ["Confirm start/end times, working hours, time zone, and grace thresholds."],
        "after_create": [],
    },
    "Shift Assignment": {
        "prerequisites": ["Employee", "Shift Type"],
        "link_fields": {"employee": "Employee", "shift_type": "Shift Type"},
        "creation_notes": ["Confirm assignment dates and avoid overlapping active shifts."],
        "after_create": ["Submit when the assignment should take effect."],
    },
    "Shift Request": {
        "prerequisites": ["Employee", "Shift Type"],
        "link_fields": {"employee": "Employee", "shift_type": "Shift Type"},
        "creation_notes": ["Confirm requested shift and effective date."],
        "after_create": ["Submit to start the configured approval workflow."],
    },
    "Employee Checkin": {
        "prerequisites": ["Employee"],
        "link_fields": {"employee": "Employee", "shift": "Shift Type"},
        "creation_notes": ["Confirm whether the event is IN or OUT and use the actual event timestamp."],
        "after_create": [],
    },
    "Leave Type": {
        "prerequisites": [],
        "link_fields": {"earning_component": "Salary Component"},
        "creation_notes": ["Set conditional encashment, earned-leave, negative-balance, and partially-paid settings consistently.", "Resolve Salary Component only when encashment or paid-leave settings require it."],
        "after_create": [],
    },
    "Leave Policy": {
        "prerequisites": ["Leave Type", "Employee Grade"],
        "link_fields": {"leave_type": "Leave Type", "employee_grade": "Employee Grade"},
        "creation_notes": ["Configure policy allocation rows using existing Leave Types and applicable employee groups/grades."],
        "after_create": [],
    },
    "Leave Period": {
        "prerequisites": [],
        "link_fields": {"company": "Company"},
        "creation_notes": ["Do not assume the active fiscal period when multiple periods overlap."],
        "after_create": [],
    },
    "Compensatory Leave Request": {
        "prerequisites": ["Employee", "Leave Type"],
        "link_fields": {"employee": "Employee", "leave_type": "Leave Type"},
        "creation_notes": ["Confirm the worked holiday/weekend date and the compensatory leave date."],
        "after_create": ["Submit when the request should enter approval workflow."],
    },
    "Leave Encashment": {
        "prerequisites": ["Employee", "Leave Type", "Company"],
        "link_fields": {"employee": "Employee", "leave_type": "Leave Type", "company": "Company"},
        "creation_notes": ["Verify available balance and encashment policy before creating."],
        "after_create": ["Submit only after payroll impact is reviewed."],
    },
    "Salary Component": {
        "prerequisites": ["Company", "Account"],
        "link_fields": {"company": "Company", "account": "Account"},
        "creation_notes": ["Confirm earning/deduction type, amount/formula behavior, and account mapping."],
        "after_create": [],
    },
    "Additional Salary": {
        "prerequisites": ["Employee", "Salary Component", "Company"],
        "link_fields": {"employee": "Employee", "salary_component": "Salary Component", "company": "Company"},
        "creation_notes": ["Confirm payroll date, amount, currency, and whether this is an earning or deduction."],
        "after_create": ["Submit when the adjustment should enter payroll."],
    },
    "Employee Advance": {
        "prerequisites": ["Employee", "Company", "Account"],
        "link_fields": {"employee": "Employee", "company": "Company", "advance_account": "Account"},
        "creation_notes": ["Confirm advance amount, repayment schedule, currency, and account."],
        "after_create": ["Submit after financial authorization."],
    },
    "Loan": {
        "prerequisites": ["Employee", "Company", "Loan Product"],
        "link_fields": {"employee": "Employee", "company": "Company", "loan_product": "Loan Product"},
        "creation_notes": ["Confirm loan product, interest, repayment schedule, and disbursement details."],
        "after_create": ["Submit only after repayment terms are reviewed."],
    },
    "Expense Claim Type": {
        "prerequisites": [],
        "link_fields": {},
        "creation_notes": ["Use a unique expense category and configure accounting defaults if required."],
        "after_create": [],
    },
    "Interview": {
        "prerequisites": ["Job Applicant", "Interview Round"],
        "link_fields": {"job_applicant": "Job Applicant", "interview_round": "Interview Round"},
        "creation_notes": ["Confirm applicant, round, interviewer, date, and time zone."],
        "after_create": ["Submit when the interview should enter workflow."],
    },
    "Interview Feedback": {
        "prerequisites": ["Job Applicant", "Interview"],
        "link_fields": {"job_applicant": "Job Applicant", "interview": "Interview"},
        "creation_notes": ["Confirm interviewer and complete the configured scorecard criteria."],
        "after_create": ["Submit when feedback is finalized."],
    },
    "Training Event": {
        "prerequisites": ["Training Program", "Company"],
        "link_fields": {"event_name": "Training Program", "company": "Company"},
        "creation_notes": ["Confirm trainer, venue/meeting link, dates, and participant capacity."],
        "after_create": ["Submit when registration should open."],
    },
    "Training Result": {
        "prerequisites": ["Employee", "Training Event"],
        "link_fields": {"employee": "Employee", "training_event": "Training Event"},
        "creation_notes": ["Record attendance, completion, score, and certificate details from the event."],
        "after_create": ["Submit when the result is final."],
    },
}


def get_creation_guidance(doctype: str) -> CreationGuidance:
    """Return curated workflow guidance, with a safe generic fallback."""
    return DOCTYPE_CREATION_GUIDANCE.get(
        doctype,
        {
            "prerequisites": [],
            "link_fields": {},
            "creation_notes": [
                "Use the live schema as authoritative.",
                "Resolve every Link field to a real existing record before creation.",
                "Ask the user to choose when multiple valid records are available.",
            ],
            "after_create": ["Check whether the live DocType is submittable before changing workflow state."],
        },
    )


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
