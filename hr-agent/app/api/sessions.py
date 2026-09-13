"""
Session Management API
Endpoints to list, create, inspect, and delete HR Agent conversation sessions.
Sessions are stored on disk by the Strands FileSessionManager under `.sessions/`.
"""

import json
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _sessions_root() -> Path:
    return Path(settings.session_storage_path)


def _session_dir(session_id: str) -> Path:
    return _sessions_root() / f"session_{session_id}"


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_session_meta(session_dir: Path) -> dict | None:
    meta_file = session_dir / "session.json"
    if not meta_file.exists():
        return None
    try:
        return _read_json(meta_file)
    except Exception:
        return None


def _read_messages(session_dir: Path) -> list[dict]:
    """Read all Strands message files from agents/agent_default/messages/ sorted by message_id."""
    messages_dir = session_dir / "agents" / "agent_default" / "messages"
    if not messages_dir.exists():
        return []

    files = sorted(
        messages_dir.glob("message_*.json"),
        key=lambda p: int(p.stem.split("_")[1]),
    )

    result = []
    for f in files:
        try:
            data = _read_json(f)
            msg = data.get("message", {})
            role = msg.get("role")
            content_blocks = msg.get("content", [])

            # Extract plain text from content blocks
            text_parts = []
            has_tool_result = False
            for block in content_blocks:
                if isinstance(block, dict):
                    if "text" in block:
                        text_parts.append(block["text"])
                    elif "toolResult" in block:
                        # Tool results — flatten nested content.
                        # These have role "user" in the LLM protocol but
                        # represent assistant/sub-agent responses for the UI.
                        has_tool_result = True
                        tr = block["toolResult"]
                        for inner in tr.get("content", []):
                            if isinstance(inner, dict) and "text" in inner:
                                text_parts.append(inner["text"])

            # Remap role: toolResult messages should display as "assistant"
            display_role = "assistant" if has_tool_result else role

            if display_role in ("user", "assistant") and text_parts:
                result.append(
                    {
                        "role": display_role,
                        "content": "\n".join(text_parts),
                        "message_id": data.get("message_id"),
                        "created_at": data.get("created_at"),
                    }
                )
        except Exception:
            continue

    return result


def _get_session_title(messages: list[dict], session_id: str) -> str:
    """Infer a human-readable title from the first user message."""
    for msg in messages:
        if msg["role"] == "user":
            text = msg["content"].strip()
            return text[:60] + ("…" if len(text) > 60 else "")
    return session_id


def _count_user_messages(messages: list[dict]) -> int:
    return sum(1 for m in messages if m["role"] == "user")


# ── Response Models ───────────────────────────────────────────────────────────


class SessionSummary(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class SessionDetail(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    messages: list[dict[str, Any]]


class CreateSessionResponse(BaseModel):
    session_id: str
    created_at: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/v1/sessions", response_model=list[SessionSummary])
async def list_sessions():
    """List all available HR Agent sessions."""
    root = _sessions_root()
    if not root.exists():
        return []

    sessions: list[SessionSummary] = []

    for entry in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not entry.is_dir() or not entry.name.startswith("session_"):
            continue
        session_id = entry.name[len("session_"):]
        meta = _read_session_meta(entry)
        if meta is None:
            continue

        messages = _read_messages(entry)
        title = _get_session_title(messages, session_id)
        count = _count_user_messages(messages)

        sessions.append(
            SessionSummary(
                session_id=session_id,
                title=title,
                created_at=meta.get("created_at", ""),
                updated_at=meta.get("updated_at", ""),
                message_count=count,
            )
        )

    return sessions


@router.post("/v1/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_session():
    """Create a new session directory with a fresh session.json."""
    session_id = str(uuid.uuid4())
    session_dir = _session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    meta = {
        "session_id": session_id,
        "session_type": "AGENT",
        "created_at": now,
        "updated_at": now,
    }

    with open(session_dir / "session.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"Created new session: {session_id}")
    return CreateSessionResponse(session_id=session_id, created_at=now)


@router.get("/v1/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str):
    """Get full session metadata and message history."""
    session_dir = _session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    meta = _read_session_meta(session_dir)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' metadata missing")

    messages = _read_messages(session_dir)
    title = _get_session_title(messages, session_id)

    return SessionDetail(
        session_id=session_id,
        title=title,
        created_at=meta.get("created_at", ""),
        updated_at=meta.get("updated_at", ""),
        message_count=_count_user_messages(messages),
        messages=messages,
    )


@router.delete("/v1/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str):
    """Permanently delete a session and all its files."""
    session_dir = _session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    try:
        shutil.rmtree(session_dir)
        logger.info(f"Deleted session: {session_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {e}")
