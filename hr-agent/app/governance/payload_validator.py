import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def clean_frappe_error(raw_error: str) -> str:
    """Clean up Frappe HTML error responses and exception strings into human-readable messages."""
    if not raw_error:
        return "Unknown error occurred in Frappe."

    # Strip HTML tags like <strong>, <a href="...">, etc.
    cleaned = re.sub(r"<[^>]+>", "", str(raw_error))
    # Strip common exception prefixes
    cleaned = re.sub(r"^frappe\.exceptions\.\w+:\s*", "", cleaned.strip())
    cleaned = re.sub(r"^ValidationError:\s*", "", cleaned.strip())
    return cleaned.strip()


def normalize_mcp_arguments(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Normalize approval arguments into the exact Pydantic schema required by Frappe MCP tools.

    Frappe MCP tools wrap their input inside a top-level 'params' dict with strict field names.
    For example:
      - frappe_create_document expects: {'params': {'doctype': str, 'fields': dict}}
      - frappe_update_document expects: {'params': {'doctype': str, 'name': str, 'fields': dict}}
      - frappe_submit_document expects: {'params': {'doctype': str, 'name': str}}
      - hrms_mark_attendance expects: {'params': {'employee': str, 'attendance_date': str, 'status': str}}
    """
    inner = arguments.get("params", arguments)
    if not isinstance(inner, dict):
        inner = {}

    if tool_name == "frappe_create_document":
        doctype = inner.get("doctype", "")
        fields = inner.get("fields") or inner.get("document") or {}
        if not str(doctype).strip():
            raise ValueError("Create document request is missing the DocType name.")
        if not isinstance(fields, dict):
            fields = {"value": fields}
        if not fields:
            raise ValueError(f"Create document request for '{doctype}' has no field values.")
        return {
            "params": {
                "doctype": str(doctype),
                "fields": fields,
            }
        }

    elif tool_name == "frappe_update_document":
        doctype = inner.get("doctype", "")
        name = inner.get("name") or inner.get("document_name") or ""
        fields = inner.get("fields") or inner.get("document") or {}
        if not str(doctype).strip() or not str(name).strip():
            raise ValueError("Update document request must include both DocType and document name.")
        if not isinstance(fields, dict):
            fields = {"value": fields}
        if not fields:
            raise ValueError(f"Update document request for '{doctype}/{name}' has no field values.")
        return {
            "params": {
                "doctype": str(doctype),
                "name": str(name),
                "fields": fields,
            }
        }

    elif tool_name in (
        "frappe_submit_document",
        "frappe_cancel_document",
        "frappe_delete_document",
        "frappe_get_document",
    ):
        doctype = inner.get("doctype", "")
        name = inner.get("name") or inner.get("document_name") or ""
        return {
            "params": {
                "doctype": str(doctype),
                "name": str(name),
            }
        }

    elif tool_name == "hrms_mark_attendance":
        allowed = {"employee", "attendance_date", "status", "working_hours"}
        emp = inner.get("employee") or inner.get("employee_id") or ""
        status = inner.get("status") or inner.get("new_status") or "Present"
        att_date = inner.get("attendance_date") or ""
        params: dict[str, Any] = {
            "employee": str(emp),
            "attendance_date": str(att_date),
            "status": str(status),
        }
        if "working_hours" in inner and inner["working_hours"] is not None:
            try:
                params["working_hours"] = float(inner["working_hours"])
            except (ValueError, TypeError):
                pass
        return {"params": params}

    elif tool_name == "hrms_apply_leave":
        allowed = {
            "employee", "leave_type", "from_date", "to_date",
            "reason", "half_day", "half_day_date"
        }
        params = {k: v for k, v in inner.items() if k in allowed}
        return {"params": params}

    # If 'params' key already present, return as is
    if "params" in arguments and isinstance(arguments["params"], dict):
        return arguments

    return {"params": arguments}


def parse_mcp_tool_result(result: dict[str, Any], tool_name: str) -> dict[str, Any]:
    """Parse MCP execution result and reliably detect Frappe API errors or validation failures."""
    is_error = result.get("isError", False)
    status = result.get("status", "success")

    # Extract text from content blocks
    content_parts = []
    for block in result.get("content", []):
        if isinstance(block, dict) and "text" in block:
            content_parts.append(block["text"])

    result_text = "\n".join(content_parts) if content_parts else str(result)

    # Try parsing result_text as JSON
    parsed_json = None
    try:
        parsed_json = json.loads(result_text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Detect errors inside the parsed JSON response
    if isinstance(parsed_json, dict):
        if "error" in parsed_json or parsed_json.get("status_code", 200) >= 400:
            raw_err = parsed_json.get("error", "Unknown error from Frappe")
            cleaned_msg = clean_frappe_error(str(raw_err))
            return {
                "status": "ERROR",
                "message": f"Frappe returned an error: {cleaned_msg}",
                "executed_tool": tool_name,
                "raw_result": result_text,
                "status_code": parsed_json.get("status_code", 400),
            }
        if parsed_json.get("status") == "error" or "exception" in parsed_json:
            raw_err = parsed_json.get("message") or parsed_json.get("exception") or result_text
            cleaned_msg = clean_frappe_error(str(raw_err))
            return {
                "status": "ERROR",
                "message": f"Frappe error: {cleaned_msg}",
                "executed_tool": tool_name,
                "raw_result": result_text,
            }

    # Detect errors from MCP envelope status
    if status == "error" or is_error:
        cleaned_msg = clean_frappe_error(result_text)
        return {
            "status": "ERROR",
            "message": f"Frappe execution error: {cleaned_msg}",
            "executed_tool": tool_name,
            "raw_result": result_text,
        }

    # Text keyword error detection
    lower_text = result_text.lower()
    if "validationerror" in lower_text or "does not exist" in lower_text or "error executing tool" in lower_text:
        cleaned_msg = clean_frappe_error(result_text)
        return {
            "status": "ERROR",
            "message": f"Frappe returned an error: {cleaned_msg}",
            "executed_tool": tool_name,
            "raw_result": result_text,
        }

    return {
        "status": "SUCCESS",
        "message": f"Operation '{tool_name}' executed successfully on Frappe HRMS.",
        "executed_tool": tool_name,
        "frappe_response": result_text,
    }


def validate_and_dry_run(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Perform pre-flight payload validation and dry-run prerequisite checks against Frappe.

    Returns:
      {
        'valid': bool,
        'dry_run_passed': bool,
        'checks': [{'name': str, 'status': 'PASSED'|'FAILED'|'WARNING', 'detail': str}],
        'errors': list[str],
        'warnings': list[str]
      }
    """
    from app.mcp.manager import mcp_manager

    checks = []
    errors = []
    warnings = []

    # A disconnected gateway must never be treated as a successful dry run.
    if not mcp_manager.client:
        checks.append({
            "name": "MCP Connection",
            "status": "WARNING",
            "detail": "MCP Gateway not connected. Frappe prerequisites could not be checked."
        })
        return {
            "valid": False,
            "dry_run_passed": False,
            "checks": checks,
            "errors": ["MCP Gateway is unavailable; the Frappe operation cannot be validated or approved."],
            "warnings": [],
        }

    inner = arguments.get("params", arguments)
    if not isinstance(inner, dict):
        inner = {}

    doctype = inner.get("doctype", "")
    fields = inner.get("fields") or inner.get("document") or {}
    if not isinstance(fields, dict):
        fields = {}

    # Check 1: DocType Schema Verification
    schema_data = None
    if doctype:
        try:
            schema_res = mcp_manager.client.call_tool_sync(
                tool_use_id="dryrun-schema",
                name="frappe_get_doctype_schema",
                arguments={"params": {"doctype": doctype}},
            )
            parsed = parse_mcp_tool_result(schema_res, "frappe_get_doctype_schema")
            if parsed["status"] == "SUCCESS":
                raw_schema = json.loads(parsed.get("frappe_response", "{}"))
                if "error" in raw_schema:
                    errors.append(f"DocType '{doctype}' does not exist in Frappe HRMS.")
                    checks.append({
                        "name": "DocType Schema",
                        "status": "FAILED",
                        "detail": f"DocType '{doctype}' not found in Frappe.",
                    })
                else:
                    schema_data = raw_schema
                    checks.append({
                        "name": "DocType Schema",
                        "status": "PASSED",
                        "detail": f"Verified '{doctype}' schema ({schema_data.get('fields_count', 0)} fields).",
                    })
            else:
                errors.append(f"Failed to fetch schema for DocType '{doctype}': {parsed.get('message')}")
                checks.append({
                    "name": "DocType Schema",
                    "status": "FAILED",
                    "detail": parsed.get("message", "Schema error"),
                })
        except Exception as e:
            warnings.append(f"Could not inspect schema for DocType '{doctype}': {e}")
            checks.append({
                "name": "DocType Schema",
                "status": "WARNING",
                "detail": str(e),
            })

    # Check 2: Field names validation against schema
    if schema_data and isinstance(fields, dict) and fields:
        valid_fieldnames = {
            f.get("fieldname")
            for f in schema_data.get("fields", [])
            if f.get("fieldname")
        }
        unknown_fields = [k for k in fields.keys() if k not in valid_fieldnames and k != "doctype"]
        required_fields = {
            f.get("fieldname")
            for f in schema_data.get("fields", [])
            if f.get("fieldname") and f.get("required")
        }
        missing_required = sorted(field for field in required_fields if field not in fields)
        if unknown_fields:
            errors.append(
                f"Field(s) {unknown_fields} do not exist on DocType '{doctype}'. "
                "Resolve the schema mismatch before approval."
            )
            checks.append({
                "name": "Field Names",
                "status": "FAILED",
                "detail": f"Unknown fields: {', '.join(unknown_fields)}",
            })
        elif missing_required:
            errors.append(
                f"Required field(s) missing for '{doctype}': {', '.join(missing_required)}."
            )
            checks.append({
                "name": "Required Fields",
                "status": "FAILED",
                "detail": f"Missing: {', '.join(missing_required)}",
            })
        else:
            checks.append({
                "name": "Field Names",
                "status": "PASSED",
                "detail": f"All {len(fields)} field name(s) are valid and required fields are present.",
            })

    # Check 3: Employee Existence check (if employee field present)
    emp_id = (
        fields.get("employee")
        or inner.get("employee")
        or inner.get("employee_id")
    )
    if emp_id:
        try:
            emp_res = mcp_manager.client.call_tool_sync(
                tool_use_id="dryrun-emp",
                name="frappe_get_document",
                arguments={"params": {"doctype": "Employee", "name": str(emp_id)}},
            )
            parsed_emp = parse_mcp_tool_result(emp_res, "frappe_get_document")
            if parsed_emp["status"] == "SUCCESS":
                emp_data = json.loads(parsed_emp.get("frappe_response", "{}"))
                if "error" in emp_data or emp_data.get("status_code", 200) >= 400:
                    errors.append(f"Employee '{emp_id}' does not exist in Frappe HRMS.")
                    checks.append({
                        "name": "Employee Existence",
                        "status": "FAILED",
                        "detail": f"Employee '{emp_id}' not found.",
                    })
                else:
                    emp_name = emp_data.get("employee_name", emp_id)
                    emp_status = emp_data.get("status", "Unknown")
                    if emp_status not in ("Active", "Probation"):
                        warnings.append(f"Employee '{emp_id}' has non-active status: '{emp_status}'.")
                        checks.append({
                            "name": "Employee Existence",
                            "status": "WARNING",
                            "detail": f"Employee {emp_name} ({emp_id}) is '{emp_status}'.",
                        })
                    else:
                        checks.append({
                            "name": "Employee Existence",
                            "status": "PASSED",
                            "detail": f"Employee {emp_name} ({emp_id}) verified (Status: {emp_status}).",
                        })
            else:
                errors.append(f"Employee '{emp_id}' does not exist in Frappe HRMS.")
                checks.append({
                    "name": "Employee Existence",
                    "status": "FAILED",
                    "detail": f"Employee '{emp_id}' not found.",
                })
        except Exception as e:
            warnings.append(f"Could not verify Employee '{emp_id}': {e}")

    # Check 4: Domain-Specific Business Rules (The Dry-Run Simulation)
    if doctype == "Salary Slip":
        # 4a: Check Salary Structure Assignment
        if emp_id:
            try:
                ssa_res = mcp_manager.client.call_tool_sync(
                    tool_use_id="dryrun-ssa",
                    name="frappe_list_documents",
                    arguments={
                        "params": {
                            "doctype": "Salary Structure Assignment",
                            "filters": {"employee": str(emp_id)},
                            "limit": 5,
                        }
                    },
                )
                parsed_ssa = parse_mcp_tool_result(ssa_res, "frappe_list_documents")
                ssa_docs = []
                if parsed_ssa["status"] == "SUCCESS":
                    try:
                        ssa_json = json.loads(parsed_ssa.get("frappe_response", "{}"))
                        ssa_docs = ssa_json.get("documents", [])
                    except Exception:
                        pass

                if not ssa_docs:
                    errors.append(
                        f"Employee '{emp_id}' has no Salary Structure Assignment. "
                        "In Frappe HRMS, salary slips cannot be created without an active Salary Structure Assignment."
                    )
                    checks.append({
                        "name": "Salary Structure Assignment",
                        "status": "FAILED",
                        "detail": f"No Salary Structure Assignment found for {emp_id}.",
                    })
                else:
                    checks.append({
                        "name": "Salary Structure Assignment",
                        "status": "PASSED",
                        "detail": f"Found active assignment: {ssa_docs[0].get('name')}.",
                    })
            except Exception as e:
                warnings.append(f"Could not verify Salary Structure Assignment for '{emp_id}': {e}")

        # 4b: Check Holiday List availability
        try:
            hl_res = mcp_manager.client.call_tool_sync(
                tool_use_id="dryrun-hl",
                name="frappe_list_documents",
                arguments={"params": {"doctype": "Holiday List", "limit": 1}},
            )
            parsed_hl = parse_mcp_tool_result(hl_res, "frappe_list_documents")
            hl_docs = []
            if parsed_hl["status"] == "SUCCESS":
                try:
                    hl_json = json.loads(parsed_hl.get("frappe_response", "{}"))
                    hl_docs = hl_json.get("documents", [])
                except Exception:
                    pass

            if not hl_docs:
                errors.append(
                    "No Holiday List is configured in Frappe for Company or Employee. "
                    "Frappe HRMS requires a Holiday List to calculate working days and payment days."
                )
                checks.append({
                    "name": "Holiday List",
                    "status": "FAILED",
                    "detail": "No Holiday List found in Frappe.",
                })
            else:
                checks.append({
                    "name": "Holiday List",
                    "status": "PASSED",
                    "detail": f"Holiday List '{hl_docs[0].get('name')}' is configured.",
                })
        except Exception as e:
            warnings.append(f"Could not verify Holiday List: {e}")

    elif doctype == "Leave Application":
        leave_type = fields.get("leave_type")
        if emp_id and leave_type:
            try:
                bal_res = mcp_manager.client.call_tool_sync(
                    tool_use_id="dryrun-leave",
                    name="hrms_get_leave_balance",
                    arguments={"params": {"employee": str(emp_id), "leave_type": str(leave_type)}},
                )
                parsed_bal = parse_mcp_tool_result(bal_res, "hrms_get_leave_balance")
                if parsed_bal["status"] == "SUCCESS":
                    bal_data = json.loads(parsed_bal.get("frappe_response", "{}"))
                    remaining = bal_data.get("remaining_leaves", 0)
                    checks.append({
                        "name": "Leave Balance",
                        "status": "PASSED" if remaining > 0 else "WARNING",
                        "detail": f"Remaining {leave_type} balance: {remaining} days.",
                    })
                    if remaining <= 0:
                        warnings.append(f"Employee '{emp_id}' has 0 or negative {leave_type} balance ({remaining} days).")
            except Exception as e:
                warnings.append(f"Could not check leave balance: {e}")

    passed = len(errors) == 0
    return {
        "valid": passed,
        "dry_run_passed": passed,
        "doctype": doctype,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }
