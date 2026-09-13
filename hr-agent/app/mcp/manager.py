import logging
from typing import Any
from mcp.client.streamable_http import StreamableHTTPTransport
from strands.tools.mcp import MCPClient
from app.config import settings

logger = logging.getLogger(__name__)


class MCPManager:
    """Manages connection and tool discovery from the Frappe MCP Server via Streamable HTTP."""

    def __init__(self):
        self.url = settings.frappe_mcp_url
        self.client: MCPClient | None = None
        self._tools: list[Any] = []
        self._tools_by_name: dict[str, Any] = {}

    def initialize(self) -> list[Any]:
        """Connect to Frappe MCP and discover ALL available tools."""
        logger.info(f"Connecting to Frappe MCP at: {self.url}")
        try:
            headers = {}
            token = settings.frappe_mcp_bearer_token
            if token:
                headers["Authorization"] = "Bearer " + token
                logger.info("Configured MCP client with bearer authentication for proxy access.")

            self.client = MCPClient(
                url=self.url,
                headers=headers if headers else None,
            )
            self.client.start()
            self._tools = self.client.list_tools_sync()
            self._tools_by_name = {
                getattr(t, "tool_name", getattr(t, "name", str(t))): t
                for t in self._tools
            }
            logger.info(
                f"Successfully connected to Frappe MCP! "
                f"Discovered {len(self._tools)} tools: {list(self._tools_by_name.keys())}"
            )
            return self._tools
        except Exception as e:
            if self.client:
                try:
                    self.client.stop()
                except Exception:
                    logger.debug("MCP client cleanup failed after initialization error.", exc_info=True)
            self.client = None
            self._tools = []
            self._tools_by_name = {}
            logger.warning(
                f"Could not connect to Frappe MCP at {self.url} during startup ({e}). "
                "MCP-backed operations will remain unavailable until the gateway is reachable."
            )
            return []

    def get_tool(self, name: str) -> Any | None:
        return self._tools_by_name.get(name)

    def get_all_tools(self) -> list[Any]:
        """Return every tool discovered from MCP — used by agents that need full access."""
        return list(self._tools)

    def _pick(self, *names: str) -> list[Any]:
        """Return tools whose names appear in `names`, skipping missing ones gracefully."""
        return [self._tools_by_name[n] for n in names if n in self._tools_by_name]

    _CORE = (
        "frappe_get_document",
        "frappe_list_documents",
        "frappe_get_link_options",
        "frappe_get_doctype_schema",
        "hrms_list_doctypes",
        "hrms_find_employee",
        "hrms_search_employees",
    )

    _WRITE = (
        "frappe_create_document",
        "frappe_update_document",
        "frappe_submit_document",
        "frappe_cancel_document",
        "frappe_delete_document",
        "frappe_run_method",
    )

    def get_tools_for_employee_agent(self) -> list[Any]:
        return self._pick(*self._CORE)

    def get_tools_for_leave_agent(self) -> list[Any]:
        return self._pick(
            *self._CORE,
            *self._WRITE,
            "hrms_get_leave_balance",
            "hrms_get_attendance",
            "hrms_mark_attendance",
        )

    def get_tools_for_payroll_agent(self) -> list[Any]:
        return self._pick(
            *self._CORE,
            *self._WRITE,
            "hrms_get_salary_slips",
            "hrms_verify_dataset",
        )

    def get_tools_for_expense_agent(self) -> list[Any]:
        return self._pick(*self._CORE, *self._WRITE)

    def get_tools_for_lifecycle_agent(self) -> list[Any]:
        return self._pick(*self._CORE, *self._WRITE)

    def get_tools_for_recruitment_agent(self) -> list[Any]:
        return self._pick(*self._CORE, *self._WRITE)

    def get_tools_for_reporting_agent(self) -> list[Any]:
        return self._pick(
            *self._CORE,
            "hrms_verify_dataset",
            "hrms_get_salary_slips",
            "hrms_get_attendance",
            "hrms_get_leave_balance",
        )


mcp_manager = MCPManager()
