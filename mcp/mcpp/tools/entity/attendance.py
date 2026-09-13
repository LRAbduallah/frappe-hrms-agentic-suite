"""HR Attendance and Shift management domain tools."""

from __future__ import annotations

import json
from typing import Callable

from mcpp.client import FrappeClient
from mcpp.tools.schema import GetAttendanceInput, MarkAttendanceInput


def register_attendance_tools(mcp, client: FrappeClient, err: Callable[[Exception], str]) -> None:
    """Register Attendance and Shift tools."""

    @mcp.tool(
        name="hrms_get_attendance",
        annotations={
            "title": "Get Attendance Records",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def hrms_get_attendance(params: GetAttendanceInput) -> str:
        """Fetch an employee's attendance logs (Present, Absent, Half Day, On Leave) for a date range."""
        try:
            docs = await client.get_list(
                "Attendance",
                fields=["name", "attendance_date", "status", "working_hours", "shift", "late_entry", "early_exit"],
                filters=[
                    ["employee", "=", params.employee],
                    ["attendance_date", ">=", params.from_date],
                    ["attendance_date", "<=", params.to_date],
                    ["docstatus", "!=", 2],
                ],
                order_by="attendance_date asc",
                limit=100,
            )
            return json.dumps({"employee": params.employee, "count": len(docs), "records": docs}, indent=2, default=str)
        except Exception as e:
            return err(e)

    @mcp.tool(
        name="hrms_mark_attendance",
        annotations={
            "title": "Mark Attendance",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def hrms_mark_attendance(params: MarkAttendanceInput) -> str:
        """Mark or update daily attendance for an employee."""
        try:
            fields = {
                "doctype": "Attendance",
                "employee": params.employee,
                "attendance_date": params.attendance_date,
                "status": params.status,
            }
            if params.working_hours is not None:
                fields["working_hours"] = params.working_hours

            doc = await client.create_doc("Attendance", fields)
            return json.dumps({"message": "Attendance marked successfully", "attendance": doc}, indent=2, default=str)
        except Exception as e:
            return err(e)
