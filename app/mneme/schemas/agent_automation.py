from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.mneme.agent.contracts import AnswerMode


class HeartbeatJobCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=4000)
    answer_mode: AnswerMode = "general_chat"
    knowledge_base_id: str | None = None
    every_seconds: int = Field(default=3600, ge=60, le=2_592_000)
    active_timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=64)
    active_start: str = "09:00"
    active_end: str = "22:00"
    isolated_session: bool = True
    light_context: bool = True
    silent_success: bool = True
    event_types: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("active_start", "active_end")
    @classmethod
    def valid_time(cls, value: str) -> str:
        parts = value.split(":")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError("time must use HH:MM")
        hour, minute = map(int, parts)
        if hour > 23 or minute > 59:
            raise ValueError("time must use HH:MM")
        return f"{hour:02d}:{minute:02d}"

    @field_validator("active_timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("unknown IANA timezone") from exc
        return value


class HeartbeatJobUpdateRequest(BaseModel):
    enabled: bool | None = None
    every_seconds: int | None = Field(default=None, ge=60, le=2_592_000)
    active_start: str | None = None
    active_end: str | None = None

    @field_validator("active_start", "active_end")
    @classmethod
    def valid_optional_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return HeartbeatJobCreateRequest.valid_time(value)


class HeartbeatJobData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: int
    name: str
    prompt: str
    answer_mode: AnswerMode
    knowledge_base_id: str | None
    session_id: str | None
    enabled: bool
    every_seconds: int
    active_timezone: str
    active_start: str
    active_end: str
    isolated_session: bool
    light_context: bool
    silent_success: bool
    event_types: list[str]
    next_run_at: datetime
    last_run_at: datetime | None
    last_run_id: str | None
    last_status: str | None
    created_at: datetime
    updated_at: datetime


class NotificationData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    kind: str
    title: str
    body: str
    action_url: str | None
    source_run_id: str | None
    metadata_json: dict[str, Any]
    read_at: datetime | None
    created_at: datetime


class NotificationListData(BaseModel):
    items: list[NotificationData]
    unread_count: int


class ToolApprovalCreateRequest(BaseModel):
    action_name: str = Field(min_length=1, max_length=120)
    action_summary: str = Field(min_length=1, max_length=2000)
    arguments: dict[str, Any] = Field(default_factory=dict)
    run_id: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=200)


class ToolApprovalDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=1000)


class ToolApprovalData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: int
    run_id: str | None
    action_name: str
    risk_level: str
    action_summary: str
    arguments_json: dict[str, Any]
    status: str
    apply_enabled: bool
    decided_at: datetime | None
    decision_reason: str | None
    created_at: datetime
    updated_at: datetime
