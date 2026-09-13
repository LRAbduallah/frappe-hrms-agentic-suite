import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.approvals import router as approvals_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.sessions import router as sessions_router
from app.config import settings
from app.mcp.manager import mcp_manager

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    force=True,
)
logger = logging.getLogger("hr_agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  Starting Frappe HR Operations Agent (Strands SDK)")
    logger.info("=" * 60)
    logger.info(f"Model:    {settings.openai_model}")
    logger.info(f"Endpoint: {settings.openai_base_url or 'https://api.openai.com/v1 (default)'}")
    logger.info(f"MCP URL:  {settings.frappe_mcp_url}")
    logger.info(f"HITL:     {settings.hitL_enabled}")

    # Discover MCP tools on startup
    mcp_manager.initialize()

    yield
    logger.info("Stopping HR Operations Agent.")


app = FastAPI(
    title="Frappe HR Operations Agent",
    description="Intelligent HR Operations Agent built with Strands Agents SDK and Frappe HRMS MCP",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(chat_router)
app.include_router(approvals_router)
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(sessions_router)
