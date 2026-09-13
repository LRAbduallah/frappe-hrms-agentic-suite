import os
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    # Private UI-to-agent API authentication key. It must never be exposed as a
    # VITE_* build variable because Vite embeds those values in browser assets.
    agent_api_key: str = Field(default_factory=lambda: os.getenv("AGENT_API_KEY", ""))
    ui_username: str = Field(default_factory=lambda: os.getenv("UI_USERNAME", "admin"))
    ui_password: str = Field(default_factory=lambda: os.getenv("UI_PASSWORD", ""))
    ui_auth_secret: str = Field(default_factory=lambda: os.getenv("UI_AUTH_SECRET", ""))
    auth_cookie_secure: bool = Field(
        default_factory=lambda: os.getenv("AUTH_COOKIE_SECURE", "false").lower()
        in ("true", "1", "yes")
    )

    # Model Provider (OpenAI Compatible)
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", "dummy-api-key"))
    openai_base_url: str | None = Field(default_factory=lambda: os.getenv("OPENAI_BASE_URL"))

    # MCP Integration
    frappe_mcp_url: str = Field(default_factory=lambda: os.getenv("FRAPPE_MCP_URL", "http://mcp-gateway:8800/mcp"))
    frappe_mcp_bearer_token: str | None = Field(
        default_factory=lambda: os.getenv("FRAPPE_MCP_BEARER_TOKEN") or os.getenv("MCP_BEARER_TOKEN")
    )

    # Business Rules
    low_leave_threshold_days: float = Field(default_factory=lambda: float(os.getenv("LOW_LEAVE_THRESHOLD_DAYS", "2.0")))
    low_leave_threshold_ratio: float = Field(default_factory=lambda: float(os.getenv("LOW_LEAVE_THRESHOLD_RATIO", "0.15")))

    # Governance
    hitL_enabled: bool = Field(default_factory=lambda: os.getenv("HITL_ENABLED", "true").lower() in ("true", "1", "yes"))
    bypass_tool_consent: bool = Field(default_factory=lambda: os.getenv("BYPASS_TOOL_CONSENT", "false").lower() in ("true", "1", "yes"))

    # Storage paths
    session_storage_path: str = Field(default_factory=lambda: os.getenv("SESSION_STORAGE_PATH", ".sessions"))
    approvals_storage_path: str = Field(default_factory=lambda: os.getenv("APPROVALS_STORAGE_PATH", ".approvals"))
    conversation_window_size: int = Field(
        default_factory=lambda: int(os.getenv("CONVERSATION_WINDOW_SIZE", "20"))
    )
    specialist_window_size: int = Field(
        default_factory=lambda: int(os.getenv("SPECIALIST_WINDOW_SIZE", "12"))
    )

    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


settings = Settings()
