import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Cookie, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_agent_api_key(
    provided_key: str | None = Security(api_key_header),
    session_cookie: str | None = Cookie(default=None, alias="hr_agent_session"),
) -> None:
    """Require the private proxy key and an authenticated UI session."""
    configured_key = settings.agent_api_key
    if not configured_key or not provided_key or not secrets.compare_digest(
        provided_key, configured_key
    ) or not verify_session(session_cookie):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )


def _sign_session(payload: str) -> str:
    return hmac.new(
        settings.ui_auth_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def create_session(username: str) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": username, "exp": int(time.time()) + 86400}).encode()
    ).decode()
    return f"{payload}.{_sign_session(payload)}"


def verify_session(token: str | None) -> bool:
    if not token or not settings.ui_auth_secret:
        return False
    try:
        payload, signature = token.split(".", 1)
        expected = _sign_session(payload)
        if not hmac.compare_digest(signature, expected):
            return False
        claims = json.loads(base64.urlsafe_b64decode(payload.encode()))
        return claims.get("sub") == settings.ui_username and claims.get("exp", 0) > time.time()
    except (
        ValueError,
        TypeError,
        binascii.Error,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        return False
