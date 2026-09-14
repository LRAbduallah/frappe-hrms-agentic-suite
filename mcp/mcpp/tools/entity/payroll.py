"""Payroll, Compensation, and Expense claim tools."""

from __future__ import annotations

import json
from typing import Callable

from mcpp.client import FrappeClient
from mcpp.tools.schema import SalarySlipsInput


def register_payroll_tools(mcp, client: FrappeClient, err: Callable[[Exception], str]) -> None:
    """Register Payroll and compensation tools."""

    @mcp.tool(
        name="hrms_get_salary_slips",
        annotations={
            "title": "Get Salary Slips",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def hrms_get_salary_slips(params: SalarySlipsInput) -> str:
        """Fetch generated Salary Slips with gross pay, total deductions, and net pay."""
        try:
            filters = [["docstatus", "!=", 2]]
            if params.employee:
                filters.append(["employee", "=", params.employee])
            if params.start_date:
                filters.append(["start_date", ">=", params.start_date])
            if params.end_date:
                filters.append(["end_date", "<=", params.end_date])

            slips = await client.get_list(
                "Salary Slip",
                fields=[
                    "name",
                    "employee",
                    "employee_name",
                    "start_date",
                    "end_date",
                    "gross_pay",
                    "total_deduction",
                    "net_pay",
                    "docstatus",
                ],
                filters=filters,
                order_by="start_date desc",
                limit=params.limit,
            )
            return json.dumps({"count": len(slips), "salary_slips": slips}, indent=2, default=str)
        except Exception as e:
            return err(e)
