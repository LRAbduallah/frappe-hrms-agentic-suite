"""Discovery tools for inspecting schemas, valid values, and available DocTypes."""

from __future__ import annotations

from typing import Callable, Optional

from mcpp.client import FrappeClient
from mcpp.compact import IGNORED_FIELD_TYPES, dumps, json_type, select_options
from mcpp.config import MCP_MAX_VALIDATION_SCHEMA_CHARS
from mcpp.doctypes import HR_DOCTYPES, format_registry_markdown, get_creation_guidance
from mcpp.tools.schema import (
    ApiCatalogInput,
    CreationPlanInput,
    LinkOptionsInput,
    ListDoctypesInput,
    SchemaInput,
)

_OPERATIONS = {
    "list": "frappe_list_documents",
    "get": "frappe_get_document",
    "create": "frappe_create_document",
    "update": "frappe_update_document",
    "lookup": "frappe_get_link_options",
    "schema": "frappe_get_doctype_schema",
    "plan": "frappe_get_creation_plan",
}


def _summarize_field(field: dict, *, compact: bool) -> dict | None:
    fieldname = field.get("fieldname")
    fieldtype = field.get("fieldtype")
    if not fieldname or fieldtype in IGNORED_FIELD_TYPES:
        return None
    required = bool(field.get("reqd"))
    if (
        compact
        and not required
        and fieldtype not in {"Link", "Table", "Select"}
        and field.get("default") is None
        and not field.get("mandatory_depends_on")
    ):
        return None
    item = {
        "fieldname": fieldname,
        "label": field.get("label"),
        "type": json_type(fieldtype),
        "fieldtype": fieldtype,
        "required": required,
    }
    if not compact:
        item.update(
            {
                "default": field.get("default"),
                "description": field.get("description") or None,
                "read_only": bool(field.get("read_only")),
                "hidden": bool(field.get("hidden")),
                "depends_on": field.get("depends_on") or None,
                "mandatory_depends_on": field.get("mandatory_depends_on") or None,
            }
        )
    elif field.get("default") is not None or field.get("mandatory_depends_on"):
        item["default"] = field.get("default")
        item["mandatory_depends_on"] = field.get("mandatory_depends_on") or None
    if fieldtype in {"Link", "Table"} and field.get("options"):
        item["target"] = field["options"]
        item["lookup"] = "frappe_get_link_options" if fieldtype == "Link" else "frappe_get_doctype_schema"
    if fieldtype == "Select":
        item["enum"] = select_options(field.get("options"))
    return item


def register_discovery_tools(mcp, client: FrappeClient, err: Callable[[Exception], str]) -> None:
    """Register discovery and schema introspection tools."""

    @mcp.tool(
        name="frappe_get_api_catalog",
        annotations={
            "title": "Get Live Frappe API Catalog",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def frappe_get_api_catalog(params: Optional[ApiCatalogInput] = None) -> str:
        """Return a compact live API map for a DocType.

        Default compact mode is a relationship catalog, not a full OpenAPI dump.
        Use frappe_get_link_options to resolve values and frappe_get_creation_plan
        immediately before a write.
        """
        request = params or ApiCatalogInput()
        catalog = {
            "openapi": "3.1.0",
            "info": {"title": "Live Frappe REST API", "version": "compact" if request.compact else "full"},
            "operations": _OPERATIONS,
            "policy": [
                "Use exact live field names.",
                "Resolve Link values with frappe_get_link_options and a search filter when possible.",
                "Call frappe_get_creation_plan before proposing a create or update.",
                "Never paste this catalog into the user-facing answer.",
            ],
        }
        if not request.doctype:
            return dumps(catalog)

        try:
            meta = await client.get_doctype_meta(request.doctype)
            if not meta:
                return dumps({"status": "ERROR", "message": f"DocType '{request.doctype}' was not found in Frappe."})

            fields = []
            optional_fieldnames = []
            for field in meta.get("fields", []):
                summarized = _summarize_field(field, compact=request.compact)
                if summarized:
                    fields.append(summarized)
                elif field.get("fieldname") and field.get("fieldtype") not in IGNORED_FIELD_TYPES:
                    optional_fieldnames.append(field["fieldname"])

            catalog.update(
                {
                    "doctype": request.doctype,
                    "is_submittable": bool(meta.get("is_submittable")),
                    "required": [field["fieldname"] for field in fields if field["required"]],
                    "fields": {field["fieldname"]: field for field in fields},
                    "child_tables": [
                        {"fieldname": field["fieldname"], "target": field.get("target")}
                        for field in fields
                        if field.get("fieldtype") == "Table"
                    ],
                    "next": ["frappe_get_link_options", "frappe_get_creation_plan"],
                }
            )
            if request.compact:
                catalog["optional_fieldnames"] = optional_fieldnames
            elif request.include_link_schemas:
                related = {}
                for field in fields:
                    target = field.get("target")
                    if not target or target in related or len(related) >= request.max_link_schemas:
                        continue
                    related_meta = await client.get_doctype_meta(target)
                    related[target] = [
                        item["fieldname"]
                        for item in (
                            _summarize_field(raw, compact=True) for raw in related_meta.get("fields", [])
                        )
                        if item
                    ]
                catalog["related"] = related
            return dumps(catalog)
        except Exception as e:
            return err(e)

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
        """List HRMS DocTypes. Compact mode returns grouped names only."""
        request = params or ListDoctypesInput()
        if not request.compact:
            return format_registry_markdown(request.category)

        grouped: dict[str, list[str]] = {}
        for name, meta in sorted(HR_DOCTYPES.items()):
            category = meta["category"]
            if request.category and request.category.lower() not in category.lower():
                continue
            grouped.setdefault(category, []).append(name)
        if not grouped:
            return dumps({"error": f"No HR DocTypes found matching category '{request.category}'."})
        return dumps({"doctypes": grouped})

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
        """Inspect live DocType fields. Compact mode returns write-relevant fields only."""
        try:
            meta = await client.get_doctype_meta(params.doctype)
            fields = []
            optional_fieldnames = []
            for field in meta.get("fields", []):
                summarized = _summarize_field(field, compact=params.compact)
                if summarized:
                    fields.append(summarized)
                elif field.get("fieldname") and field.get("fieldtype") not in IGNORED_FIELD_TYPES:
                    optional_fieldnames.append(field["fieldname"])
            payload = {
                "doctype": params.doctype,
                "is_submittable": bool(meta.get("is_submittable")),
                "title_field": meta.get("title_field"),
                "fields_count": len(fields),
                "fields": fields,
            }
            if params.compact:
                payload["optional_fieldnames"] = optional_fieldnames
            if params.doctype not in HR_DOCTYPES:
                payload["note"] = f"'{params.doctype}' is not in the curated HR registry. Verify exact spelling."
            return dumps(
                payload,
                max_chars=(
                    MCP_MAX_VALIDATION_SCHEMA_CHARS
                    if not params.compact
                    else None
                ),
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
        """Build a live creation plan. Compact mode samples Link options instead of dumping them."""
        try:
            meta = await client.get_doctype_meta(params.doctype)
            if not meta:
                return dumps({"status": "ERROR", "message": f"DocType '{params.doctype}' was not found in Frappe."})

            guidance = get_creation_guidance(params.doctype)
            fields = []
            optional_fieldnames = []
            link_options = {}
            lookup_errors = []

            for field in meta.get("fields", []):
                summarized = _summarize_field(field, compact=params.compact)
                if summarized:
                    fields.append(summarized)
                elif field.get("fieldname") and field.get("fieldtype") not in IGNORED_FIELD_TYPES:
                    optional_fieldnames.append(field["fieldname"])

                fieldname = field.get("fieldname")
                fieldtype = field.get("fieldtype")
                should_lookup = fieldtype == "Link" and field.get("options") and (
                    params.include_optional_links or bool(field.get("reqd"))
                )
                if not should_lookup:
                    continue
                try:
                    values = await client.get_list(
                        field["options"],
                        fields=["name"],
                        limit=params.link_option_limit,
                        order_by="name asc",
                    )
                    options = [row["name"] for row in values if row.get("name")]
                    link_options[fieldname] = {
                        "target": field["options"],
                        "options": options,
                        "count_returned": len(options),
                        "choice_required": len(options) > 1,
                        "blocked": len(options) == 0,
                        "required": bool(field.get("reqd")),
                        "lookup": "frappe_get_link_options",
                    }
                except Exception as exc:
                    lookup_errors.append(
                        {
                            "fieldname": fieldname,
                            "target": field["options"],
                            "required": bool(field.get("reqd")),
                            "error": str(exc),
                        }
                    )

            payload = {
                "status": "READY",
                "doctype": params.doctype,
                "is_submittable": bool(meta.get("is_submittable")),
                "title_field": meta.get("title_field"),
                "required_fields": [field["fieldname"] for field in fields if field["required"]],
                "fields": fields,
                "child_tables": [
                    {"fieldname": field["fieldname"], "target": field.get("target")}
                    for field in fields
                    if field.get("fieldtype") == "Table"
                ],
                "link_options": link_options,
                "prerequisites": guidance["prerequisites"],
                "workflow_guidance": {
                    "link_fields": guidance["link_fields"],
                    "creation_notes": guidance["creation_notes"],
                    "after_create": guidance["after_create"],
                },
                "selection_policy": (
                    "Use only returned existing Link options. Ask the user when choice_required is true. "
                    "Call frappe_get_link_options with search to resolve more values."
                ),
                "interaction_policy": {
                    "ask_at_most_one_grouped_question": True,
                    "auto_use_live_default": True,
                    "auto_use_single_available_link": True,
                    "ask_only_for": [
                        "missing mandatory fields without a live default",
                        "multiple valid Link choices",
                        "business decisions that cannot be inferred safely",
                    ],
                    "do_not_ask": [
                        "fields already supplied by the user",
                        "optional fields with no business impact",
                        "whether to proceed after an approval proposal is created",
                    ],
                },
                "lookup_errors": lookup_errors,
                "can_create": (
                    not any(error["required"] for error in lookup_errors)
                    and not any(item["required"] and item["blocked"] for item in link_options.values())
                ),
            }
            if params.compact:
                payload["optional_fieldnames"] = optional_fieldnames
            return dumps(payload)
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
        """Fetch existing names for a Link target. Always prefer a search filter."""
        try:
            filters = [["name", "like", f"%{params.search}%"]] if params.search else None
            docs = await client.get_list(
                params.target_doctype,
                fields=["name"],
                filters=filters,
                limit=params.limit,
            )
            options = [doc["name"] for doc in docs if doc.get("name")]
            return dumps(
                {
                    "target_doctype": params.target_doctype,
                    "count": len(options),
                    "options": options,
                    "search": params.search,
                    "hint": "If multiple options exist, ask the user. Do not pick the first silently.",
                }
            )
        except Exception as e:
            return err(e)
