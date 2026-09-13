"""Discovery tools for inspecting schemas, valid values, and available DocTypes."""

from __future__ import annotations

import json
from typing import Callable, Optional

from mcpp.client import FrappeClient
from mcpp.doctypes import HR_DOCTYPES, format_registry_markdown, get_creation_guidance
from mcpp.tools.schema import CreationPlanInput, LinkOptionsInput, ListDoctypesInput, SchemaInput


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
                    "description": f.get("description") or None,
                    "read_only": bool(f.get("read_only")),
                    "hidden": bool(f.get("hidden")),
                    "depends_on": f.get("depends_on") or None,
                    "mandatory_depends_on": f.get("mandatory_depends_on") or None,
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
        name="frappe_get_creation_plan",
        annotations={
            "title": "Plan DocType Creation",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def frappe_get_creation_plan(params: CreationPlanInput) -> str:
        """Build a live, schema-aware creation plan before writing a Frappe document.

        Returns required fields, field types, child-table structure, workflow state,
        curated prerequisites, and current valid records for Link fields. The agent
        must use the returned values rather than inventing company, employee,
        department, or other linked record names. If multiple link options are
        returned, ask the user to choose unless they explicitly supplied a value.
        """
        try:
            meta = await client.get_doctype_meta(params.doctype)
            if not meta:
                return json.dumps({
                    "status": "ERROR",
                    "message": f"DocType '{params.doctype}' was not found in Frappe.",
                }, indent=2)

            guidance = get_creation_guidance(params.doctype)
            ignored_types = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Heading", "Fold"}
            fields = []
            link_options = {}
            lookup_errors = []

            for field in meta.get("fields", []):
                fieldname = field.get("fieldname")
                fieldtype = field.get("fieldtype")
                if not fieldname or fieldtype in ignored_types:
                    continue
                item = {
                    "fieldname": fieldname,
                    "label": field.get("label"),
                    "fieldtype": fieldtype,
                    "required": bool(field.get("reqd")),
                    "options": field.get("options") or None,
                    "default": field.get("default"),
                    "description": field.get("description") or None,
                    "read_only": bool(field.get("read_only")),
                    "hidden": bool(field.get("hidden")),
                    "depends_on": field.get("depends_on") or None,
                    "mandatory_depends_on": field.get("mandatory_depends_on") or None,
                }
                if fieldtype == "Link":
                    item["link_target"] = field.get("options")
                    should_lookup = params.include_optional_links or bool(field.get("reqd"))
                    if should_lookup and field.get("options"):
                        try:
                            values = await client.get_list(
                                field["options"],
                                fields=["name"],
                                limit=params.link_option_limit,
                                order_by="name asc",
                            )
                            options = [row["name"] for row in values if row.get("name")]
                            link_options[fieldname] = {
                                "target_doctype": field["options"],
                                "options": options,
                                "count_returned": len(options),
                                "choice_required": len(options) > 1,
                                "blocked": len(options) == 0,
                                "required": bool(field.get("reqd")),
                            }
                        except Exception as exc:
                            lookup_errors.append({
                                "fieldname": fieldname,
                                "target_doctype": field["options"],
                                "required": bool(field.get("reqd")),
                                "error": str(exc),
                            })
                fields.append(item)

            required_fields = [field["fieldname"] for field in fields if field["required"]]
            child_tables = [
                {"fieldname": field["fieldname"], "options": field["options"]}
                for field in fields
                if field["fieldtype"] == "Table"
            ]
            return json.dumps({
                "status": "READY",
                "doctype": params.doctype,
                "is_submittable": bool(meta.get("is_submittable")),
                "title_field": meta.get("title_field"),
                "required_fields": required_fields,
                "fields": fields,
                "child_tables": child_tables,
                "link_options": link_options,
                "prerequisites": guidance["prerequisites"],
                "workflow_guidance": {
                    "link_fields": guidance["link_fields"],
                    "creation_notes": guidance["creation_notes"],
                    "after_create": guidance["after_create"],
                },
                "selection_policy": (
                    "Use only returned existing Link options. Ask the user to choose when "
                    "count_returned is greater than one; never select the first option silently."
                ),
                "lookup_errors": lookup_errors,
                "can_create": (
                    not any(error["required"] for error in lookup_errors)
                    and not any(item["required"] and item["blocked"] for item in link_options.values())
                ),
            }, indent=2, default=str)
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
