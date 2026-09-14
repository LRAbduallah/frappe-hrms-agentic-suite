from fastapi import APIRouter
from app.config import settings
from app.mcp.manager import mcp_manager

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Liveness probe: verifies the service is running."""
    return {
        "status": "healthy",
        "service": "strands-hr-agent",
        "env": settings.app_env,
    }


@router.get("/ready")
async def ready():
    """Readiness probe: verifies model provider configuration and MCP readiness."""
    mcp_tools_count = len(mcp_manager._tools)
    return {
        "status": "ready",
        "model": settings.openai_model,
        "base_url": settings.openai_base_url or "https://api.openai.com/v1 (default)",
        "mcp_url": settings.frappe_mcp_url,
        "discovered_mcp_tools": mcp_tools_count,
        "hitl_enabled": settings.hitL_enabled,
    }
