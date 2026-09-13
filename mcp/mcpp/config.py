"""Configuration and environment management for Frappe HR MCP."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Search for .env in current dir, parent dir, or package root
env_paths = [
    Path.cwd() / ".env",
    Path(__file__).resolve().parent.parent / ".env",
]
for p in env_paths:
    if p.exists():
        load_dotenv(dotenv_path=p, override=False)
        break
else:
    load_dotenv(override=False)

FRAPPE_BASE_URL: str = os.environ.get("FRAPPE_BASE_URL", "http://localhost:8000").rstrip("/")
FRAPPE_API_KEY: str = os.environ.get("FRAPPE_API_KEY", "")
FRAPPE_API_SECRET: str = os.environ.get("FRAPPE_API_SECRET", "")
FRAPPE_REQUEST_TIMEOUT: float = float(os.environ.get("FRAPPE_REQUEST_TIMEOUT", "30.0"))

# Server Mode: "production" (safe, no delete) or "admin" (full CRUD + bulk setup)
ServerMode = Literal["production", "admin"]
FRAPPE_MCP_MODE: ServerMode = (
    "admin" if os.environ.get("FRAPPE_MCP_MODE", "").lower() == "admin" else "production"
)
