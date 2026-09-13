"""Discovery tools for inspecting schemas, valid values, and available DocTypes."""

from __future__ import annotations

import json
from typing import Callable, Optional

from mcpp.client import FrappeClient
from mcpp.doctypes import HR_DOCTYPES, format_registry_markdown
from mcpp.tools.schema import LinkOptionsInput, ListDoctypesInput, SchemaInput


def register_discovery_tools(mcp, client: FrappeClient, err: Callable[[Exception], str]) -> None:
    """Register discovery and schema introspection tools."""

    @mcp.tool(
        name="hrms_list_doctypes",
        annotations={
            "title": "List Available HR DocTypes",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def hrms_list_doctypes(params: Optional[ListDoctypesInput] = None) -> str:
        """List all HRMS DocTypes supported by this server, categorized by domain.

        Always call this tool first if you are not 100% sure of the exact Frappe
        DocType name (e.g. 'Shift Assignment' vs 'Shift Request', or 'Leave Allocation').
        """
        cat = params.category if params else None
        return format_registry_markdown(cat)

    @mcp.tool(
        name="frappe_get_doctype_schema",
        annotations={
            "title": "Get DocType Schema",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def frappe_get_doctype_schema(params: SchemaInput) -> str:
        """Inspect the schema of any DocType: fieldnames, labels, fieldtypes,
        required status, and link options.

        Call this before creating or updating a document to ensure correct field names
        and mandatory fields instead of guessing.
        """
        try:
            meta = await client.get_doctype_meta(params.doctype)
            fields = meta.get("fields", [])
            ignored_types = {
                "Section Break",
                "Column Break",
                "Tab Break",
                "HTML",
                "Button",
                "Heading",
                "Fold",
            }
            simplified = [
                {
                    "fieldname": f.get("fieldname"),
                    "label": f.get("label"),
                    "fieldtype": f.get("fieldtype"),
                    "required": bool(f.get("reqd")),
                    "options": f.get("options") or None,
                    "default": f.get("default"),
                }
                for f in fields
                if f.get("fieldtype") not in ignored_types and f.get("fieldname")
            ]

            note = ""
            if params.doctype not in HR_DOCTYPES:
                note = f"Note: '{params.doctype}' is not in the curated HR registry. Verify exact spelling."

            return json.dumps(
                {
                    "doctype": params.doctype,
                    "is_submittable": bool(meta.get("is_submittable")),
                    "title_field": meta.get("title_field"),
                    "fields_count": len(simplified),
                    "fields": simplified,
                    "note": note or None,
                },
                indent=2,
                default=str,
            )
        except Exception as e:
            return err(e)

    @mcp.tool(
        name="frappe_get_link_options",
        annotations={
            "title": "Get Valid Values for Link Field",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def frappe_get_link_options(params: LinkOptionsInput) -> str:
        """Fetch real, existing primary keys/names for a Link-type field.

        For example, before creating an Employee, check valid 'Department' or 'Designation'
        records so you don't enter non-existent values.
        """
        try:
            filters = None
            if params.search:
                filters = [["name", "like", f"%{params.search}%"]]

            docs = await client.get_list(
                params.target_doctype,
                fields=["name"],
                filters=filters,
                limit=params.limit,
            )
            options = [d["name"] for d in docs if "name" in d]
            return json.dumps(
                {"target_doctype": params.target_doctype, "count": len(options), "options": options},
                indent=2,
            )
        except Exception as e:
            return err(e)
