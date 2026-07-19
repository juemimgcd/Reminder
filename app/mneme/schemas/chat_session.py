from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.mneme.memoria.contracts import AnswerMode
from app.mneme.schemas.chat import ChatCitationItem, ChatSourceItem, QueryRouteDecision


class ChatMessageData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    user_id: int
    knowledge_base_id: str | None
    role: str
    content: str
    agent_run_id: str | None = None
    sequence_no: int | None = None
    sources: list[ChatSourceItem] = Field(default_factory=list)
    citations: list[ChatCitationItem] = Field(default_factory=list)
    tool_calls: list[dict] = Field(default_factory=list)
    route: QueryRouteDecision | None = None
    model_config_id: str | None = None
    confidence: float | None = None
    uncertainty: str | None = None
    insufficient_evidence: bool = False
    created_at: datetime


class ChatSessionData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    knowledge_base_id: str | None
    answer_mode: AnswerMode
    multi_agent_enabled: bool = False
    title: str | None = None
    message_count: int
    last_message_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ChatSessionListData(BaseModel):
    items: list[ChatSessionData]
    total: int


class ChatSessionDetailData(BaseModel):
    session: ChatSessionData
    messages: list[ChatMessageData]


class ChatSessionCreateRequest(BaseModel):
    knowledge_base_id: str | None = None
    title: str | None = Field(default=None, max_length=255)
    answer_mode: AnswerMode = "kb_qa"
    multi_agent_enabled: bool = False

    @model_validator(mode="after")
    def require_scope_for_private_modes(self):
        if self.answer_mode != "general_chat" and self.knowledge_base_id is None:
            raise ValueError("knowledge_base_id is required for this answer mode")
        return self


class ChatSessionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    archived: bool | None = None
    answer_mode: AnswerMode | None = None
    multi_agent_enabled: bool | None = None


class ChatSessionMessageRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=4, ge=1, le=10)
    answer_mode: AnswerMode | None = None
    execution_mode: Literal["single", "multi"] | None = None
    model_config_id: str | None = None
    retry_message_id: str | None = None
    regenerate_message_id: str | None = None
    client_request_id: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def mutually_exclusive_replay(self):
        if self.retry_message_id is not None and self.regenerate_message_id is not None:
            raise ValueError("retry_message_id and regenerate_message_id are mutually exclusive")
        return self


class AgentRunControlRequest(BaseModel):
    mode: Literal["steer", "followup", "interrupt"]
    question: str | None = Field(default=None, min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=10)
    answer_mode: AnswerMode | None = None
    execution_mode: Literal["single", "multi"] | None = None
    client_request_id: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def require_instruction_for_scheduled_controls(self):
        if self.mode in {"steer", "followup"} and self.question is None:
            raise ValueError("question is required for steer and followup controls")
        return self


class ChatMessageRememberData(BaseModel):
    message_id: str
    requested: bool
