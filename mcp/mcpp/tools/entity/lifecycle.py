"""Employee search, onboarding, separation, and appraisal tools."""

from __future__ import annotations

import json
from typing import Callable

from mcpp.client import FrappeClient
from mcpp.tools.schema import FindEmployeeInput


def register_lifecycle_tools(mcp, client: FrappeClient, err: Callable[[Exception], str]) -> None:
    """Register Employee search and lifecycle tools."""

    @mcp.tool(
        name="hrms_find_employee",
        annotations={
            "title": "Find Employee",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def hrms_find_employee(params: FindEmployeeInput) -> str:
        """Search employees by name, ID, email, or department."""
        try:
            fields = [
                "name",
                "employee_name",
                "company_email",
                "personal_email",
                "department",
                "designation",
                "status",
                "date_of_joining",
                "reports_to",
            ]

            # Try name match first
            filters: list = [["employee_name", "like", f"%{params.query}%"]]
            if params.status:
                filters.append(["status", "=", params.status])

            docs = await client.get_list("Employee", fields=fields, filters=filters, limit=params.limit)

            # Fallback to ID or email match
            if not docs:
                filters = [["name", "like", f"%{params.query}%"]]
                if params.status:
                    filters.append(["status", "=", params.status])
                docs = await client.get_list("Employee", fields=fields, filters=filters, limit=params.limit)

            if not docs:
                filters = [["company_email", "like", f"%{params.query}%"]]
                if params.status:
                    filters.append(["status", "=", params.status])
                docs = await client.get_list("Employee", fields=fields, filters=filters, limit=params.limit)

            return json.dumps({"query": params.query, "count": len(docs), "employees": docs}, indent=2, default=str)
        except Exception as e:
            return err(e)
