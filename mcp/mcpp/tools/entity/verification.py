"""Read-only verification and scenario metrics for HR test datasets."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from typing import Any, Callable

from mcpp.client import FrappeClient
from mcpp.tools.schema import VerifyHRDatasetInput


def _days_between(start: str, end: str) -> int:
	return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1


def register_verification_tools(mcp, client: FrappeClient, err: Callable[[Exception], str]) -> None:
	"""Register read-only aggregate checks used after data population."""

	@mcp.tool(
		name="hrms_verify_dataset",
		annotations={
			"title": "Verify HR Dataset",
			"readOnlyHint": True,
			"destructiveHint": False,
			"idempotentHint": True,
			"openWorldHint": True,
		},
	)
	async def hrms_verify_dataset(params: VerifyHRDatasetInput) -> str:
		"""Summarize employees, compensation, leave utilization, attendance, and potential LOP risk."""
		try:
			start_date = date.fromisoformat(params.from_date)
			end_date = date.fromisoformat(params.to_date)
			if start_date > end_date:
				raise ValueError("from_date must be on or before to_date")
			employee_filters: list[list[Any]] = []
			if params.employee_filter:
				employee_filters.append(["employee_name", "like", f"%{params.employee_filter}%"])
			employees = await client.get_list(
				"Employee",
				fields=["name", "employee_name", "department", "designation", "status"],
				filters=employee_filters or None,
				limit=params.limit,
			)

			employee_ids = [row.get("name") for row in employees if row.get("name")]
			allocations: list[dict[str, Any]] = []
			applications: list[dict[str, Any]] = []
			attendance: list[dict[str, Any]] = []
			assignments: list[dict[str, Any]] = []
			for employee_id in employee_ids:
				allocations.extend(await client.get_list(
					"Leave Allocation",
					fields=["employee", "leave_type", "total_leaves_allocated", "from_date", "to_date", "docstatus"],
					filters=[["employee", "=", employee_id], ["docstatus", "=", 1]],
					limit=100,
				))
				applications.extend(await client.get_list(
					"Leave Application",
					fields=["employee", "leave_type", "from_date", "to_date", "status", "docstatus"],
					filters=[
						["employee", "=", employee_id],
						["from_date", ">=", params.from_date],
						["to_date", "<=", params.to_date],
						["docstatus", "=", 1],
					],
					limit=100,
				))
				attendance.extend(await client.get_list(
					"Attendance",
					fields=["employee", "attendance_date", "status", "docstatus"],
					filters=[
						["employee", "=", employee_id],
						["attendance_date", ">=", params.from_date],
						["attendance_date", "<=", params.to_date],
						["docstatus", "!=", 2],
					],
					limit=500,
				))
				assignments.extend(await client.get_list(
					"Salary Structure Assignment",
					fields=["employee", "base", "salary_structure", "from_date", "docstatus"],
					filters=[["employee", "=", employee_id], ["docstatus", "!=", 2]],
					order_by="from_date desc",
					limit=1,
				))

			by_employee: dict[str, dict[str, Any]] = {}
			for employee in employees:
				by_employee[employee["name"]] = {
					**employee,
					"allocated": 0,
					"used": 0,
					"attendance_total": 0,
					"attendance_present": 0,
					"attendance_absent": 0,
					"salary_base": None,
				}
			for allocation in allocations:
				row = by_employee.get(allocation.get("employee"))
				if row:
					row["allocated"] += float(allocation.get("total_leaves_allocated") or 0)
			for application in applications:
				row = by_employee.get(application.get("employee"))
				if row:
					row["used"] += _days_between(application["from_date"], application["to_date"])
			for record in attendance:
				row = by_employee.get(record.get("employee"))
				if row:
					row["attendance_total"] += 1
					if record.get("status") == "Present":
						row["attendance_present"] += 1
					elif record.get("status") == "Absent":
						row["attendance_absent"] += 1
			for assignment in assignments:
				row = by_employee.get(assignment.get("employee"))
				if row and row["salary_base"] is None:
					row["salary_base"] = assignment.get("base")

			for row in by_employee.values():
				row["remaining"] = row["allocated"] - row["used"]
				row["attendance_rate"] = (
					round(row["attendance_present"] / row["attendance_total"] * 100, 2)
					if row["attendance_total"] else None
				)
				row["potential_lop_days"] = max(0, row["attendance_absent"] - max(0, row["remaining"]))

			rows = list(by_employee.values())
			bases = [float(row["salary_base"]) for row in rows if row["salary_base"] is not None]
			result = {
				"period": {"from_date": params.from_date, "to_date": params.to_date},
				"employee_count": len(rows),
				"employees_by_department": dict(Counter(row.get("department") or "Unassigned" for row in rows)),
				"employees_by_designation": dict(Counter(row.get("designation") or "Unassigned" for row in rows)),
				"salary_base": {
					"minimum": min(bases) if bases else None,
					"maximum": max(bases) if bases else None,
					"average": round(sum(bases) / len(bases), 2) if bases else None,
				},
				"employees_with_leave_allocation": sum(row["allocated"] > 0 for row in rows),
				"zero_leave_balance": [row["name"] for row in rows if row["remaining"] <= 0],
				"low_leave_balance": [row["name"] for row in rows if 0 < row["remaining"] <= 5],
				"high_leave_utilization": [
					row["name"] for row in rows if row["allocated"] > 0 and row["used"] / row["allocated"] >= 0.8
				],
				"attendance_concerns": [row["name"] for row in rows if row["attendance_rate"] is not None and row["attendance_rate"] < 80],
				"potential_lop_risk": [
					{"employee": row["name"], "days": row["potential_lop_days"]}
					for row in rows if row["potential_lop_days"] > 0
				],
				"employees": rows,
			}
			return json.dumps(result, indent=2, default=str)
		except Exception as e:
			return err(e)