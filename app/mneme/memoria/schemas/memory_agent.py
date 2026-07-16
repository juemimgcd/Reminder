from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

AnswerMode = Literal[
    "kb_qa",
    "memory_query",
    "profile_query",
    "analysis_query",
    "general_chat",
]
ConversationRole = Literal["user", "assistant"]
MemoryAgentEventType = Literal[
    "document.projection.upserted",
    "document.memory.observed",
    "document.deleted",
    "knowledge_base.deleted",
    "conversation.completed",
    "conversation.deleted",
    "user.memory_requested",
    "user.memory_settings.changed",
]


class ModelInvocationConfig(BaseModel):
    provider: str
    base_url: str
    model_name: str
    api_key: SecretStr = Field(exclude=True)
    temperature: float = 0.0
    context_window: int = Field(default=64000, ge=1000, le=1000000)


class MemoryAgentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=128)
    event_type: MemoryAgentEventType
    schema_version: Literal["1"] = "1"
    occurred_at: datetime
    owner_id: int = Field(gt=0)
    knowledge_base_id: str | None = None
    payload: dict[str, Any]

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_must_have_timezone(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value


class DocumentChunkPayload(BaseModel):
    chunk_id: str
    chunk_index: int
    content: str
    content_hash: str
    page_no: int | None = None
    section_path: list[str] = Field(default_factory=list)


class DocumentProjectionPayload(BaseModel):
    projection_id: str
    document_id: str
    document_version: str
    file_name: str
    batch_index: int = Field(ge=0)
    batch_count: int = Field(gt=0)
    aggregate_hash: str
    chunks: list[DocumentChunkPayload]


class DocumentMemoryObservedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=128)
    projection_id: str = Field(min_length=1, max_length=64)
    chunk_id: str = Field(min_length=1, max_length=128)
    document_version: str = Field(min_length=1, max_length=128)
    content_hash: str = Field(min_length=64, max_length=64)
    excerpt_hash: str = Field(min_length=64, max_length=64)
    observed_at: datetime
    excerpt: str = Field(min_length=1, max_length=20_000)


class EventReceipt(BaseModel):
    event_id: str
    accepted: bool
    duplicate: bool


class ConversationMessageData(BaseModel):
    message_id: str = Field(min_length=1, max_length=128)
    role: ConversationRole
    content: str = Field(min_length=1, max_length=20_000)


class ConversationContextData(BaseModel):
    summary: str = Field(default="", max_length=20_000)
    summary_through_message_id: str | None = Field(default=None, max_length=128)
    messages: list[ConversationMessageData] = Field(default_factory=list, max_length=24)


class MemoryAgentAnswerRequest(BaseModel):
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


class MemoryAgentAnswerResponse(BaseModel):
    answer: str
    mode: AnswerMode
    route: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float
    uncertainty: str | None = None
    insufficient_evidence: bool = False
    memory_ids: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    run_id: str


class MemoryAgentStreamEvent(BaseModel):
    type: Literal["phase", "final", "error"]
    run_id: str | None = None
    phase: str | None = None
    status: str | None = None
    code: str | None = None
    response: MemoryAgentAnswerResponse | None = None


class CanonicalMemoryData(BaseModel):
    memory_id: str
    knowledge_base_id: str | None
    memory_type: str
    subject: str
    predicate: str
    value: str
    confidence: float
    status: str
    active_revision_id: str
    created_at: datetime
    updated_at: datetime


class MemoryCandidateData(BaseModel):
    candidate_id: str
    knowledge_base_id: str | None
    memory_type: str
    subject: str
    predicate: str
    value: str
    confidence: float
    status: str
    created_at: datetime
    decided_at: datetime | None


class GovernedMemoryPage(BaseModel):
    items: list[CanonicalMemoryData]
    next_cursor: str | None = None
    total: int = 0


class MemoryCandidatePage(BaseModel):
    items: list[MemoryCandidateData]
    next_cursor: str | None = None
    total: int = 0
    pending_count: int = 0


class MemoryRevisionData(BaseModel):
    revision_id: str
    subject: str
    predicate: str
    value: str
    valid_from: datetime
    valid_to: datetime | None
    reason: str


class MemoryEvidenceData(BaseModel):
    evidence_id: str
    revision_id: str
    source_type: str
    source_id: str
    source_document_id: str | None
    excerpt: str
    source_time: datetime


class MemoryDetailData(BaseModel):
    memory: CanonicalMemoryData
    revisions: list[MemoryRevisionData]
    evidence: list[MemoryEvidenceData]


class CandidateActionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=256)
    confirmation_token: str = Field(min_length=1, max_length=4096)


class MemoryRevisionRequest(CandidateActionRequest):
    subject: str = Field(min_length=1, max_length=2000)
    predicate: str = Field(min_length=1, max_length=2000)
    value: str = Field(min_length=1, max_length=10000)
    confidence: float | None = Field(default=None, ge=0, le=1)


class MemoryActionRequest(CandidateActionRequest):
    pass


MemoryConfirmationAction = Literal[
    "confirm_candidate",
    "reject_candidate",
    "revise_memory",
    "invalidate_memory",
    "hard_delete_memory",
    "purge_source",
    "purge_knowledge_base",
    "purge_account",
]


class MemoryConfirmationRequest(BaseModel):
    action: MemoryConfirmationAction
    target_id: str | None = Field(default=None, min_length=1, max_length=128)
    knowledge_base_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_target(self) -> "MemoryConfirmationRequest":
        requires_target = self.action != "purge_account"
        if requires_target != (self.target_id is not None):
            raise ValueError("target_id must be supplied except for account purge")
        if self.action == "purge_account" and self.knowledge_base_id is not None:
            raise ValueError("account purge cannot be knowledge-base scoped")
        return self


class MemoryConfirmationData(BaseModel):
    action: MemoryConfirmationAction
    target_id: str
    expires_at: datetime
    confirmation_token: str


class MemoryPurgeRequest(BaseModel):
    source_id: str | None = Field(default=None, min_length=1, max_length=128)
    knowledge_base_id: str | None = Field(default=None, min_length=1, max_length=64)
    scope_knowledge_base_id: str | None = Field(default=None, max_length=64)
    purge_account: bool = False
    reason: str = Field(min_length=1, max_length=256)
    confirmation_token: str = Field(min_length=1, max_length=4096)

    @model_validator(mode="after")
    def exactly_one_selector(self) -> "MemoryPurgeRequest":
        if sum((self.source_id is not None, self.knowledge_base_id is not None, self.purge_account)) != 1:
            raise ValueError("exactly one purge selector is required")
        if self.source_id is None and self.scope_knowledge_base_id is not None:
            raise ValueError("source scope is only valid for source purge")
        return self


class ConversationMemorySettingsUpdate(BaseModel):
    automatic_conversation_memory: bool


class ConversationMemorySettingsData(BaseModel):
    automatic_conversation_memory: bool
    applied: bool
