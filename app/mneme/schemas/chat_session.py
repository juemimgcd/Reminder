from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.mneme.agent.contracts import AnswerMode
from app.mneme.schemas.chat import ChatCitationItem, ChatSourceItem, QueryRouteDecision


class ChatMessageData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    user_id: int
    knowledge_base_id: str | None
    role: str
    content: str
    sources: list[ChatSourceItem] = Field(default_factory=list)
    citations: list[ChatCitationItem] = Field(default_factory=list)
    route: QueryRouteDecision | None = None
    model_config_id: str | None = None
    agent_run_id: str | None = None
    created_at: datetime


class ChatSessionData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    knowledge_base_id: str | None
    answer_mode: AnswerMode
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

    @model_validator(mode="after")
    def require_scope_for_private_modes(self):
        if self.answer_mode != "general_chat" and self.knowledge_base_id is None:
            raise ValueError("knowledge_base_id is required for this answer mode")
        return self


class ChatSessionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    archived: bool | None = None
    answer_mode: AnswerMode | None = None


class ChatSessionMessageRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=4, ge=1, le=10)
    answer_mode: AnswerMode = "kb_qa"
    model_config_id: str | None = None
    retry_message_id: str | None = None


class ChatMessageRememberData(BaseModel):
    message_id: str
    requested: bool
