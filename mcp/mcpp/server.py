"""Server factory and orchestration for Frappe HR MCP."""

from __future__ import annotations

import json
import logging
from typing import Optional

from mcp.server.mcpserver import MCPServer

from mcpp.client import FrappeAPIError, FrappeClient
from mcpp.config import FRAPPE_MCP_MODE, ServerMode
from mcpp.tools.discovery import register_discovery_tools
from mcpp.tools.documents import register_document_tools
from mcpp.tools.entity.attendance import register_attendance_tools
from mcpp.tools.entity.leave import register_leave_tools
from mcpp.tools.entity.lifecycle import register_lifecycle_tools
from mcpp.tools.entity.payroll import register_payroll_tools
from mcpp.tools.entity.verification import register_verification_tools
from mcpp.tools.workflow import register_workflow_tools


logger = logging.getLogger(__name__)


def _format_error(e: Exception) -> str:
    """Format exceptions into safe JSON responses for LLM consumption."""
    if isinstance(e, FrappeAPIError):
        return json.dumps({"error": e.message, "status_code": e.status_code}, indent=2)
    return json.dumps({"error": f"Internal Error ({type(e).__name__}): {e}"}, indent=2)


def build_server(mode: Optional[ServerMode] = None) -> MCPServer:
    """Create and assemble the MCP server instance configured for the given mode."""
    active_mode: ServerMode = mode or FRAPPE_MCP_MODE
    logger.info("Building MCP server: mode=%s", active_mode)

    instructions = (
        f"You are connected to a Frappe HRMS instance operating in '{active_mode.upper()}' mode.\n\n"
        "1. Schema Discovery: Before creating or modifying documents, call 'hrms_list_doctypes' "
        "when the exact DocType is uncertain, then call 'frappe_get_creation_plan'. It returns "
        "the live installed schema, required fields, child tables, workflow rules, prerequisites, "
        "and current valid Link values. Use 'frappe_get_doctype_schema' for detail and "
        "'frappe_get_link_options' for a targeted lookup.\n"
        "2. Link Selection: Never invent or silently choose Company, Employee, Department, "
        "Designation, Leave Type, Currency, Cost Center, or any other Link value. Use only "
        "records returned by Frappe. If multiple options exist, ask the user to choose; if none "
        "exist, stop and explain which prerequisite must be created first.\n"
        "3. Workflow Compliance: Submittable documents (Leave Applications, Salary Slips, "
        "Attendance) require 'frappe_submit_document' to take legal/financial effect.\n"
    )

    if active_mode == "production":
        instructions += (
            "4. Safety Policy: PRODUCTION STREAM MODE IS ACTIVE. Deletion of documents is disabled. "
            "Only Read, Create, and Update operations are permitted.\n"
        )
    else:
        instructions += (
            "4. Admin Policy: ADMIN / SETUP MODE IS ACTIVE. Full CRUD is enabled, including "
            "frappe_delete_document and frappe_bulk_create_documents for data seeding.\n"
        )

    mcp = MCPServer(f"frappe_hr_mcp_{active_mode}", instructions=instructions)
    client = FrappeClient()
    logger.info("Frappe API client initialized: base_url=%s timeout=%s", client.base_url, client.timeout)

    # Register tool modules
    logger.info("Registering MCP tool modules")
    register_discovery_tools(mcp, client, _format_error)
    register_document_tools(mcp, client, _format_error, mode=active_mode)
    register_workflow_tools(mcp, client, _format_error)
    register_leave_tools(mcp, client, _format_error)
    register_attendance_tools(mcp, client, _format_error)
    register_payroll_tools(mcp, client, _format_error)
    register_verification_tools(mcp, client, _format_error)
    register_lifecycle_tools(mcp, client, _format_error)
    logger.info("MCP server ready: mode=%s", active_mode)

    return mcp
