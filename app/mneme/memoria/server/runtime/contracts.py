from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.mneme.memoria.server.contracts.answers import AnswerRequest, ConversationContextData
from app.mneme.memoria.server.contracts.common import AnswerMode, ModelInvocationConfig
from app.mneme.memoria.server.retrieval.contracts import RetrievedEvidence

RunStatus = Literal["running", "completed", "failed"]
RunPhase = Literal["validate", "retrieve", "generate", "citations", "complete"]


class RetrievalPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    document: bool
    memory: bool
    profile: bool
    relations: bool
    max_expansions: int = Field(ge=0, le=1)

    @property
    def uses_private_sources(self) -> bool:
        return self.document or self.memory or self.profile or self.relations

    def for_source(self, source_type: str) -> "RetrievalPlan":
        if source_type not in {"document", "memory", "profile", "relation"}:
            raise ValueError("unsupported retrieval source")
        return RetrievalPlan(
            document=source_type == "document",
            memory=source_type == "memory",
            profile=source_type == "profile",
            relations=source_type == "relation",
            max_expansions=0,
        )


class RetrievalRequest(BaseModel):
    request_id: str
    owner_id: int
    knowledge_base_id: str | None
    mode: AnswerMode
    question: str = Field(exclude=True, repr=False)
    top_k: int
    plan: RetrievalPlan
    expansion_index: int = Field(default=0, ge=0, le=1)
    temporal_scope: Literal["current", "history"] = "current"


class ToolExecutionContext(BaseModel):
    request_id: str
    owner_id: int = Field(gt=0)
    knowledge_base_id: str | None = None
    mode: AnswerMode
    top_k: int = Field(default=4, ge=1, le=10)
    plan: RetrievalPlan
    allow_action_proposals: bool = False


class GenerationRequest(BaseModel):
    request_id: str
    mode: AnswerMode
    question: str = Field(exclude=True, repr=False)
    evidence: list[RetrievedEvidence] = Field(repr=False)
    conversation: ConversationContextData = Field(default_factory=ConversationContextData, repr=False)
    model: ModelInvocationConfig | None = Field(default=None, exclude=True)
    allow_model_fallback: bool = False
    execution_mode: Literal["single", "multi"] = "single"
    max_model_calls: int = Field(default=12, ge=1, le=32)
    max_prompt_tokens: int = Field(default=200_000, ge=512, le=1_000_000)
    max_completion_tokens: int = Field(default=32_000, ge=128, le=100_000)
    tool_context: ToolExecutionContext | None = Field(default=None, exclude=True, repr=False)


class GeneratedAnswer(BaseModel):
    answer: str
    route: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertainty: str | None = None
    insufficient_evidence: bool = False
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    cost: float = Field(default=0, ge=0)
    model_attempts: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_evidence: list[RetrievedEvidence] = Field(default_factory=list, exclude=True, repr=False)
    selected_provider: str | None = None
    selected_model: str | None = None
    fallback_used: bool = False
    stop_reason: str | None = None
    execution_mode: Literal["single", "multi"] = "single"
    degraded: bool = False
    role_attempts: list[dict[str, Any]] = Field(default_factory=list)
    budget_usage: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class CitationResult(BaseModel):
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertainty: str | None = None
    insufficient_evidence: bool = False


class AnswerRunData(BaseModel):
    run_id: str
    request_id: str
    trace_id: str
    owner_id: int
    knowledge_base_id: str | None
    session_id: str | None
    message_id: str
    mode: AnswerMode
    status: RunStatus
    current_phase: RunPhase
    phase_durations_ms: dict[str, int]
    source_ids: list[str]
    expansion_count: int
    confidence: float | None
    uncertainty: str | None
    insufficient_evidence: bool | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost: float | None
    error_code: str | None
    response_json: dict[str, Any] | None
    model_attempts: list[dict[str, Any]]
    selected_provider: str | None
    selected_model: str | None
    fallback_used: bool
    execution_mode: Literal["single", "multi"]
    role_attempts: list[dict[str, Any]]
    budget_usage: dict[str, Any]
    degraded: bool
    stop_reason: str | None
    created_at: datetime
    started_at: datetime
    retrieval_completed_at: datetime | None
    generation_completed_at: datetime | None
    citations_completed_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None


def retrieval_request(request: AnswerRequest, plan: RetrievalPlan, *, expansion_index: int) -> RetrievalRequest:
    return RetrievalRequest(
        request_id=request.request_id,
        owner_id=request.owner_id,
        knowledge_base_id=request.knowledge_base_id,
        mode=request.answer_mode,
        question=request.question,
        top_k=request.top_k,
        plan=plan,
        expansion_index=expansion_index,
    )
