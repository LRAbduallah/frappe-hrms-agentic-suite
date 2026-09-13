"""HR Leave management domain tools (Leave Balance, Applications, Allocations)."""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Callable

from mcpp.client import FrappeClient
from mcpp.tools.schema import ApplyLeaveInput, LeaveBalanceInput


def register_leave_tools(mcp, client: FrappeClient, err: Callable[[Exception], str]) -> None:
    """Register Leave domain tools."""

    @mcp.tool(
        name="hrms_get_leave_balance",
        annotations={
            "title": "Get Employee Leave Balance",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def hrms_get_leave_balance(params: LeaveBalanceInput) -> str:
        """Fetch remaining leave balances across all allocated leave types for an employee."""
        try:
            current_date = params.date or date.today().isoformat()
            allocations = await client.get_list(
                "Leave Allocation",
                fields=["name", "leave_type", "total_leaves_allocated", "from_date", "to_date"],
                filters=[["employee", "=", params.employee], ["docstatus", "=", 1]],
                limit=50,
            )

            balances = []
            for alloc in allocations:
                lt = alloc.get("leave_type")
                rpc_params: dict[str, Any] = {
                    "employee": params.employee,
                    "leave_type": lt,
                    "date": current_date,
                }
                try:
                    balance = await client.call_method(
                        "hrms.hr.doctype.leave_application.leave_application.get_leave_balance_on",
                        params=rpc_params,
                    )
                except Exception:
                    balance = "N/A"

                balances.append(
                    {
                        "leave_type": lt,
                        "allocated": alloc.get("total_leaves_allocated"),
                        "balance": balance,
                        "valid_from": alloc.get("from_date"),
                        "valid_to": alloc.get("to_date"),
                    }
                )

            return json.dumps({"employee": params.employee, "balances": balances}, indent=2, default=str)
        except Exception as e:
            return err(e)

    @mcp.tool(
        name="hrms_apply_leave",
        annotations={
            "title": "Apply for Leave",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def hrms_apply_leave(params: ApplyLeaveInput) -> str:
        """Create a Leave Application in Open status; submit it separately with frappe_submit_document."""
        try:
            fields: dict[str, Any] = {
                "doctype": "Leave Application",
                "employee": params.employee,
                "leave_type": params.leave_type,
                "from_date": params.from_date,
                "to_date": params.to_date,
                "half_day": 1 if params.half_day else 0,
            }
            if params.reason:
                fields["description"] = params.reason
            if params.half_day_date:
                fields["half_day_date"] = params.half_day_date

            doc = await client.create_doc("Leave Application", fields)
            return json.dumps(
                {
                    "message": "Leave application created successfully (Status: Open).",
                    "application": doc,
                },
                indent=2,
                default=str,
            )
        except Exception as e:
            return err(e)
