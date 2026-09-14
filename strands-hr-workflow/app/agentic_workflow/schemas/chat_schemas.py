from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: Literal["user", "assistant"]
    content: str
    tool_metadata: dict[str, Any] | list[Any] | None = None
    error_message: str | None = None
    created_at: datetime


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    created_at: datetime
    updated_at: datetime


class ChatMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class ChatTurnResponse(BaseModel):
    session_id: str
    status: Literal["success", "error"]
    assistant_response: str | None = None
    messages: list[ChatMessageResponse] = Field(default_factory=list)
    available_tools: list[str] = Field(default_factory=list)
    error_message: str | None = None