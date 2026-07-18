from typing import Any, Literal

from pydantic import BaseModel, Field

from app.mneme.memoria.server.contracts.common import AnswerMode, ModelInvocationConfig

ConversationRole = Literal["user", "assistant"]


class ConversationMessageData(BaseModel):
    message_id: str = Field(min_length=1, max_length=128)
    role: ConversationRole
    content: str = Field(min_length=1, max_length=20_000)


class ConversationContextData(BaseModel):
    summary: str = Field(default="", max_length=20_000)
    summary_through_message_id: str | None = Field(default=None, max_length=128)
    messages: list[ConversationMessageData] = Field(default_factory=list, max_length=24)


class AnswerRequest(BaseModel):
    request_id: str
    trace_id: str = Field(default="", max_length=64)
    owner_id: int
    knowledge_base_id: str | None = None
    session_id: str | None = None
    message_id: str
    question: str = Field(min_length=1)
    answer_mode: AnswerMode
    top_k: int = Field(default=4, ge=1, le=10)
    allow_model_fallback: bool = False
    conversation: ConversationContextData = Field(default_factory=ConversationContextData)
    model: ModelInvocationConfig | None = Field(default=None, exclude=True)


class AnswerResponse(BaseModel):
    answer: str
    mode: AnswerMode
    route: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float
    uncertainty: str | None = None
    insufficient_evidence: bool = False
    memory_ids: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    stop_reason: str | None = None
    run_id: str


class AnswerStreamEvent(BaseModel):
    type: Literal["phase", "delta", "final", "error"]
    schema_version: Literal["2"] = "2"
    sequence: int = Field(ge=1)
    name: str
    run_id: str | None = None
    phase: str | None = None
    status: str | None = None
    content: str | None = None
    public_payload: dict[str, Any] = Field(default_factory=dict)
    code: str | None = None
    response: AnswerResponse | None = None
