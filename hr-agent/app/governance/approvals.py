import json
import logging
import os
import tempfile
from contextvars import ContextVar, Token
import uuid
from typing import Any
from app.config import settings
from app.models.schemas import ApprovalRequest, ApprovalStatus, RiskLevel

logger = logging.getLogger(__name__)
_active_session_id: ContextVar[str | None] = ContextVar("approval_session_id", default=None)


def set_approval_session(session_id: str) -> Token:
    """Bind approval proposals created during an agent turn to its chat session."""
    return _active_session_id.set(session_id)


def reset_approval_session(token: Token) -> None:
    _active_session_id.reset(token)


class ApprovalStore:
    def __init__(self, storage_dir: str | None = None):
        self.storage_dir = storage_dir or settings.approvals_storage_path
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, approval_id: str) -> str:
        return os.path.join(self.storage_dir, f"{approval_id}.json")

    def create(
        self,
        session_id: str,
        action: str,
        tool_name: str,
        arguments: dict[str, Any],
        reason: str,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        user_id: str = "hr_user",
        preflight: dict[str, Any] | None = None,
    ) -> ApprovalRequest:
        approval_id = str(uuid.uuid4())[:8]
        effective_session_id = (
            _active_session_id.get()
            or session_id
        )
        req = ApprovalRequest(
            id=approval_id,
            session_id=effective_session_id,
            user_id=user_id,
            action=action,
            tool_name=tool_name,
            arguments=arguments,
            reason=reason,
            risk_level=risk_level,
            status=ApprovalStatus.PENDING,
            preflight=preflight,
        )
        self.save(req)
        logger.info(f"Created ApprovalRequest {approval_id} for {tool_name}")
        return req

    def save(self, req: ApprovalRequest) -> None:
        payload = req.model_dump_json(indent=2)
        fd, temp_path = tempfile.mkstemp(prefix=f".{req.id}.", suffix=".tmp", dir=self.storage_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self._get_path(req.id))
        except Exception:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass
            raise

    def get(self, approval_id: str) -> ApprovalRequest | None:
        path = self._get_path(approval_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return ApprovalRequest.model_validate_json(f.read())

    def list_all(self, session_id: str | None = None) -> list[ApprovalRequest]:
        approvals = []
        if not os.path.exists(self.storage_dir):
            return approvals
        for fname in os.listdir(self.storage_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(self.storage_dir, fname), "r", encoding="utf-8") as f:
                        req = ApprovalRequest.model_validate_json(f.read())
                        if session_id is None or req.session_id == session_id:
                            approvals.append(req)
                except Exception as e:
                    logger.error(f"Error reading approval file {fname}: {e}")
        return sorted(approvals, key=lambda x: x.created_at, reverse=True)

    def recent_failures(self, session_id: str, limit: int = 3) -> list[ApprovalRequest]:
        """Return failed approvals for the active session for agent follow-up context."""
        return [
            req
            for req in self.list_all(session_id=session_id)
            if req.status == ApprovalStatus.FAILED
        ][:limit]


approval_store = ApprovalStore()
