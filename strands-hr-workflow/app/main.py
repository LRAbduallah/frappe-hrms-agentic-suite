

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.api import api_router
from app.agentic_workflow.services.mcp_service import discover_mcp_tool_names
from app.configuration.config import get_settings
from app.database.session import get_session_factory

app = FastAPI(
  title="Strands HR Management System",
  description="HR management APIs with leave management as the current scope.",
  version="1.0.0",
)
app.include_router(api_router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
  """Return a lightweight process health response without contacting dependencies."""
  return {"status": "ok"}


@app.get("/ready", tags=["system"])
async def readiness_check() -> dict[str, object]:
  settings = get_settings()
  checks: dict[str, object] = {}

  try:
    session_factory = get_session_factory(settings.DATABASE_URL)
    with session_factory() as session:
      session.execute(text("SELECT 1"))
    checks["database"] = "ok"
  except Exception as exc:
    checks["database"] = str(exc)

  try:
    tool_names = discover_mcp_tool_names(settings)
    required_tools = {"hrms_find_employee", "hrms_get_leave_balance"}
    missing_tools = sorted(required_tools - tool_names)
    if missing_tools:
      checks["mcp"] = {"missing_tools": missing_tools}
    else:
      checks["mcp"] = {"status": "ok", "discovered_tools": len(tool_names)}
  except Exception as exc:
    checks["mcp"] = str(exc)

  failed_checks = [name for name, result in checks.items() if result != "ok" and not (
    isinstance(result, dict) and result.get("status") == "ok"
  )]
  if failed_checks:
    raise HTTPException(
      status_code=503,
      detail={"status": "not_ready", "failed_checks": failed_checks, "checks": checks},
    )

  return {"status": "ready", "checks": checks}