from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.mneme.schemas.chat import ChatCitationItem, ChatSourceItem, QueryRouteDecision


class ChatMessageData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    user_id: int
    knowledge_base_id: str
    role: str
    content: str
    sources: list[ChatSourceItem] = Field(default_factory=list)
    citations: list[ChatCitationItem] = Field(default_factory=list)
    route: QueryRouteDecision | None = None
    model_config_id: str | None = None
    created_at: datetime


class ChatSessionData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    knowledge_base_id: str
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
    knowledge_base_id: str
    title: str | None = Field(default=None, max_length=255)


class ChatSessionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    archived: bool | None = None


class ChatSessionMessageRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=4, ge=1, le=10)
