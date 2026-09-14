import secrets

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from pydantic import BaseModel

from app.auth import create_session, verify_session
from app.config import settings


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(request: LoginRequest, response: Response):
    if (
        not settings.ui_password
        or not secrets.compare_digest(request.username, settings.ui_username)
        or not secrets.compare_digest(request.password, settings.ui_password)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    response.set_cookie(
        key="hr_agent_session",
        value=create_session(request.username),
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=86400,
        path="/",
    )
    return {"username": settings.ui_username}


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie("hr_agent_session", path="/")


@router.get("/me")
async def current_user(session_cookie: str | None = Cookie(default=None, alias="hr_agent_session")):
    if not verify_session(session_cookie):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return {"username": settings.ui_username}
