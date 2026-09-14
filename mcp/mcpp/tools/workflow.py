"""Workflow and document lifecycle tools (Submit, Cancel, Amend, Status transitions)."""

from __future__ import annotations

import json
from typing import Callable

from mcpp.client import FrappeClient
from mcpp.tools.schema import DocActionInput, HistoryInput


def register_workflow_tools(mcp, client: FrappeClient, err: Callable[[Exception], str]) -> None:
    """Register workflow lifecycle management tools."""

    @mcp.tool(
        name="frappe_submit_document",
        annotations={
            "title": "Submit Document",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def frappe_submit_document(params: DocActionInput) -> str:
        """Submit a draft document (changing docstatus from 0 [Draft] to 1 [Submitted])."""
        try:
            res = await client.update_doc(params.doctype, params.name, {"docstatus": 1})
            return json.dumps(
                {
                    "message": f"Document {params.name} submitted successfully.",
                    "doctype": params.doctype,
                    "name": params.name,
                    "docstatus": res.get("docstatus", 1),
                },
                indent=2,
            )
        except Exception as e:
            return err(e)

    @mcp.tool(
        name="frappe_cancel_document",
        annotations={
            "title": "Cancel Submitted Document",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def frappe_cancel_document(params: DocActionInput) -> str:
        """Cancel a submitted document (changing docstatus from 1 [Submitted] to 2 [Cancelled])."""
        try:
            res = await client.update_doc(params.doctype, params.name, {"docstatus": 2})
            return json.dumps(
                {
                    "message": f"Document {params.name} cancelled successfully.",
                    "doctype": params.doctype,
                    "name": params.name,
                    "docstatus": res.get("docstatus", 2),
                },
                indent=2,
            )
        except Exception as e:
            return err(e)

    @mcp.tool(
        name="frappe_get_document_history",
        annotations={
            "title": "Get Document Timeline & Comments",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def frappe_get_document_history(params: HistoryInput) -> str:
        """Fetch timeline comments, versions, and communications related to a document."""
        try:
            logs = await client.get_list(
                "Comment",
                fields=["name", "comment_type", "comment_email", "content", "creation"],
                filters=[["reference_doctype", "=", params.doctype], ["reference_name", "=", params.name]],
                order_by="creation desc",
                limit=50,
            )
            return json.dumps(
                {"doctype": params.doctype, "name": params.name, "timeline_count": len(logs), "history": logs},
                indent=2,
                default=str,
            )
        except Exception as e:
            return err(e)
