"""Generic Document CRUD tools with mode-based access (admin delete vs production safety)."""

from __future__ import annotations

import json
from typing import Any, Callable

from mcpp.client import FrappeClient
from mcpp.config import ServerMode
from mcpp.tools.schema import (
    BulkCreateInput,
    CreateDocInput,
    DeleteDocInput,
    GetDocInput,
    ListDocsInput,
    UpdateDocInput,
)


def register_document_tools(
    mcp, client: FrappeClient, err: Callable[[Exception], str], mode: ServerMode = "production"
) -> None:
    """Register generic document CRUD tools."""

    @mcp.tool(
        name="frappe_list_documents",
        annotations={
            "title": "List Documents",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def frappe_list_documents(params: ListDocsInput) -> str:
        """List and search documents of any DocType with filters, field selection, and pagination."""
        try:
            docs = await client.get_list(
                params.doctype,
                fields=params.fields,
                filters=params.filters,
                order_by=params.order_by,
                limit=params.limit,
                offset=params.offset,
            )
            return json.dumps(
                {"count": len(docs), "offset": params.offset, "limit": params.limit, "documents": docs},
                indent=2,
                default=str,
            )
        except Exception as e:
            return err(e)

    @mcp.tool(
        name="frappe_get_document",
        annotations={
            "title": "Get Document",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def frappe_get_document(params: GetDocInput) -> str:
        """Fetch the full content and child tables of a single document by DocType and name."""
        try:
            doc = await client.get_doc(params.doctype, params.name)
            return json.dumps(doc, indent=2, default=str)
        except Exception as e:
            return err(e)

    @mcp.tool(
        name="frappe_create_document",
        annotations={
            "title": "Create Document",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def frappe_create_document(params: CreateDocInput) -> str:
        """Create a new document of any DocType. Returns the created record with assigned name ID."""
        try:
            doc = await client.create_doc(params.doctype, params.fields)
            return json.dumps(doc, indent=2, default=str)
        except Exception as e:
            return err(e)

    @mcp.tool(
        name="frappe_update_document",
        annotations={
            "title": "Update Document",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def frappe_update_document(params: UpdateDocInput) -> str:
        """Update fields on an existing document."""
        try:
            doc = await client.update_doc(params.doctype, params.name, params.fields)
            return json.dumps(doc, indent=2, default=str)
        except Exception as e:
            return err(e)

    # -----------------------------------------------------------------------
    # Admin / Setup Mode Only Tools
    # -----------------------------------------------------------------------
    if mode == "admin":

        @mcp.tool(
            name="frappe_delete_document",
            annotations={
                "title": "Delete Document (Admin Mode Only)",
                "readOnlyHint": False,
                "destructiveHint": True,
                "idempotentHint": True,
                "openWorldHint": True,
            },
        )
        async def frappe_delete_document(params: DeleteDocInput) -> str:
            """Permanently delete a document. Available only in Admin mode."""
            try:
                await client.delete_doc(params.doctype, params.name)
                return json.dumps(
                    {"deleted": True, "doctype": params.doctype, "name": params.name, "mode": "admin"}
                )
            except Exception as e:
                return err(e)

        @mcp.tool(
            name="frappe_bulk_create_documents",
            annotations={
                "title": "Bulk Create Documents (Admin Mode Only)",
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
                "openWorldHint": True,
            },
        )
        async def frappe_bulk_create_documents(params: BulkCreateInput) -> str:
            """Bulk create records for initial data seeding."""
            created: list[dict[str, Any]] = []
            errors: list[dict[str, Any]] = []
            for i, fields in enumerate(params.documents):
                try:
                    res = await client.create_doc(params.doctype, fields)
                    created.append({"index": i, "name": res.get("name"), "status": "success"})
                except Exception as ex:
                    errors.append({"index": i, "error": str(ex)})

            return json.dumps(
                {
                    "doctype": params.doctype,
                    "total": len(params.documents),
                    "created_count": len(created),
                    "error_count": len(errors),
                    "created": created,
                    "errors": errors,
                },
                indent=2,
            )
