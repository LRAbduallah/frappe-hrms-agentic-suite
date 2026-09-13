import json
import logging
import os
import tempfile
import uuid
from typing import Any
from app.config import settings
from app.models.schemas import ApprovalRequest, ApprovalStatus, RiskLevel

logger = logging.getLogger(__name__)


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
        req = ApprovalRequest(
            id=approval_id,
            session_id=session_id,
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


approval_store = ApprovalStore()
