"""Helpers that keep MCP tool results small enough for long-running agents."""

from __future__ import annotations

import json
from typing import Any

from mcpp.config import MCP_MAX_TOOL_RESULT_CHARS

IGNORED_FIELD_TYPES = {
    "Section Break",
    "Column Break",
    "Tab Break",
    "HTML",
    "Button",
    "Heading",
    "Fold",
}

INTERNAL_DOC_KEYS = {
    "modified",
    "modified_by",
    "owner",
    "creation",
    "idx",
    "docstatus",
    "doctype",
    "_user_tags",
    "_comments",
    "_assign",
    "_liked_by",
    "_seen",
    "lft",
    "rgt",
    "old_parent",
}

_JSON_TYPES = {
    "Check": "boolean",
    "Int": "integer",
    "Float": "number",
    "Currency": "number",
    "Percent": "number",
    "Date": "string",
    "Datetime": "string",
    "Time": "string",
    "Table": "array",
}


def dumps(payload: Any, *, max_chars: int | None = None) -> str:
    """Serialize tool output as compact JSON and hard-cap size."""
    text = json.dumps(payload, separators=(",", ":"), default=str, ensure_ascii=False)
    limit = max_chars or MCP_MAX_TOOL_RESULT_CHARS
    if len(text) <= limit:
        return text
    return json.dumps(
        {
            "truncated": True,
            "original_chars": len(text),
            "hint": "Narrow fields, filters, or limits. Prefer frappe_get_creation_plan over dumping catalogs.",
            "preview": text[: max(200, limit - 280)],
        },
        separators=(",", ":"),
        ensure_ascii=False,
    )


def json_type(fieldtype: str | None) -> str:
    return _JSON_TYPES.get(fieldtype or "", "string")


def slim_document(doc: Any) -> Any:
    """Drop Frappe bookkeeping fields that inflate agent context."""
    if isinstance(doc, list):
        return [slim_document(item) for item in doc]
    if not isinstance(doc, dict):
        return doc
    slim: dict[str, Any] = {}
    for key, value in doc.items():
        if key in INTERNAL_DOC_KEYS or key.startswith("_"):
            continue
        slim[key] = slim_document(value) if isinstance(value, (dict, list)) else value
    return slim


def select_options(raw: str | None) -> list[str]:
    return [option for option in (raw or "").split("\n") if option]
