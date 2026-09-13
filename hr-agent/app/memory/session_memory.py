"""Compact working memory stored outside the model prompt."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class SessionMemory:
    """Persist a few session facts so long chats do not replay full MCP dumps."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.path = Path(settings.session_storage_path) / f"session_{session_id}" / "working_memory.json"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            logger.debug("Could not read working memory for session %s", self.session_id, exc_info=True)
            return {}

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def context_block(self) -> str:
        data = self.load()
        facts = []
        for key in ("company", "employee", "department", "doctype"):
            value = data.get(key)
            if value:
                facts.append(f"{key}={value}")
        failure = data.get("last_failure")
        if failure:
            facts.append(f"last_failure={str(failure)[:240]}")
        if not facts:
            return ""
        return "SESSION WORKING MEMORY:\n" + "; ".join(facts)

    def record_failure(self, message: str) -> None:
        data = self.load()
        data["last_failure"] = str(message)[:240]
        self.save(data)
