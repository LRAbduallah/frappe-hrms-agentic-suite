from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

from pydantic import Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )
    OPENAI_MODEL: str = Field("gpt-4o-mini")
    OPENAI_API_KEY: str = Field(...)
    OPENAI_BASE_URL: str | None = Field(None)
    FRAPPE_MCP_URL: str
    MCP_EMPLOYEE_QUERY: str = Field("*")
    EMAIL_API_BASE_URL: str = Field("http://127.0.0.1:8001")
    DATABASE_URL: str = Field("sqlite:///data/HR_management.db")
    WORKFLOW_COOLDOWN_DAYS: float = Field(0.0, ge=0.0)
    LOW_LEAVE_THRESHOLD_DAYS: float = Field(2.0)
    LOW_LEAVE_THRESHOLD_RATIO: float = Field(0.15)
    HITL_ENABLED: bool = Field(True)
    BYPASS_TOOL_CONSENT: bool = Field(True)
    CHAT_HISTORY_LIMIT: int = Field(5, ge=1, le=50)
    MCP_BEARER_TOKEN: str = Field(...)
    CORS_ORIGINS: str = Field(
        "http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173"
    )

def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]