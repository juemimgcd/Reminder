from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.mneme.memoria.server.retrieval.contracts import RetrievedEvidence

ExecutionMode = Literal["single", "multi"]
RequestedExecutionMode = Literal["auto", "single", "multi"]
EvidenceSource = Literal["document", "memory", "profile", "relation"]
RetrievalRole = Literal[
    "document_retriever",
    "memory_retriever",
    "profile_retriever",
    "relation_retriever",
]


class MultiAgentBudgetLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    deadline_seconds: float = Field(default=20, gt=0, le=120)
    source_timeout_seconds: float = Field(default=8, gt=0, le=60)
    max_model_calls: int = Field(default=4, ge=1, le=16)
    max_prompt_tokens: int = Field(default=12_000, ge=512, le=200_000)
    max_completion_tokens: int = Field(default=3_600, ge=128, le=32_000)
    max_retrieval_top_k: int = Field(default=16, ge=1, le=40)
    max_estimated_cost: float = Field(default=1.0, ge=0, le=100)
    max_supplemental_rounds: Literal[0, 1] = 1


class BudgetUsage(BaseModel):
    model_calls: int = Field(default=0, ge=0)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    retrieval_top_k: int = Field(default=0, ge=0)
    estimated_cost: float = Field(default=0, ge=0)
    supplemental_rounds: int = Field(default=0, ge=0, le=1)
    elapsed_ms: int = Field(default=0, ge=0)


class SourceAssignment(BaseModel):
    role: RetrievalRole
    source_type: EvidenceSource
    query: str = Field(exclude=True, repr=False)
    top_k: int = Field(ge=1, le=10)
    required: bool = False


class CoordinatorDecision(BaseModel):
    execution_mode: ExecutionMode
    reason_code: str = Field(max_length=64)
    assignments: list[SourceAssignment] = Field(default_factory=list, max_length=4)
    allow_supplemental: bool = False


class EvidenceBundle(BaseModel):
    agent_role: RetrievalRole
    source_type: EvidenceSource
    query: str = Field(exclude=True, repr=False)
    evidence: list[RetrievedEvidence] = Field(
        default_factory=list,
        exclude=True,
        repr=False,
    )
    coverage: float = Field(ge=0, le=1)
    uncertainty: list[str] = Field(default_factory=list, max_length=8)
    elapsed_ms: int = Field(ge=0)
    degraded: bool = False
    error_code: str | None = Field(default=None, max_length=64)


class DroppedEvidence(BaseModel):
    evidence_id: str
    reason_code: Literal["duplicate", "budget", "lower_relevance"]


class EvidenceConflict(BaseModel):
    source_type: EvidenceSource
    source_id: str
    evidence_ids: list[str] = Field(min_length=2, max_length=8)
    reason_code: Literal["content_mismatch"] = "content_mismatch"


class JudgedEvidenceSet(BaseModel):
    evidence: list[RetrievedEvidence] = Field(
        default_factory=list,
        exclude=True,
        repr=False,
    )
    kept_evidence_ids: list[str] = Field(default_factory=list)
    dropped: list[DroppedEvidence] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    coverage: float = Field(ge=0, le=1)
    missing_sources: list[EvidenceSource] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list, max_length=12)
    needs_supplemental: bool = False


class RoleAttempt(BaseModel):
    role: str = Field(max_length=64)
    source_type: EvidenceSource | None = None
    status: Literal["completed", "failed", "degraded"]
    elapsed_ms: int = Field(ge=0)
    evidence_count: int = Field(default=0, ge=0)
    error_code: str | None = Field(default=None, max_length=64)
    supplemental_round: int = Field(default=0, ge=0, le=1)


class MultiAgentExecutionResult(BaseModel):
    judged: JudgedEvidenceSet
    role_attempts: list[RoleAttempt]
    budget_usage: BudgetUsage
    degraded: bool = False
    stop_reason: str = Field(default="multi_agent_completed", max_length=64)
