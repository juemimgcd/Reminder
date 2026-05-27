from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    case_id: str = Field(..., description="Stable eval case ID")
    question: str = Field(..., description="User question")
    expected_answer: str | None = Field(default=None, description="Reference answer or answer notes")
    expected_source_chunk_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    difficulty: Literal["easy", "medium", "hard"] = "medium"


class EvalDataset(BaseModel):
    dataset_id: str = Field(..., description="Stable eval dataset ID")
    name: str = Field(..., description="Dataset name")
    description: str | None = None
    cases: list[EvalCase] = Field(default_factory=list)


class EvalPrediction(BaseModel):
    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    debug: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float | None = None
    token_cost: float | None = None
    llm_call_count: int | None = None
    retrieval_count: int | None = None


class RetrievalEvalMetrics(BaseModel):
    recall_at_k: float
    mrr: float
    ndcg: float
    source_hit: bool
    expected_source_count: int
    retrieved_source_count: int


class GenerationEvalMetrics(BaseModel):
    faithfulness: float
    citation_accuracy: float
    answer_relevance: float
    abstention_accuracy: float


class EngineeringEvalMetrics(BaseModel):
    latency_ms: float | None = None
    token_cost: float | None = None
    llm_call_count: int | None = None
    retrieval_count: int | None = None


class EvalResult(BaseModel):
    case_id: str
    question: str
    retrieval: RetrievalEvalMetrics
    generation: GenerationEvalMetrics
    engineering: EngineeringEvalMetrics
    tags: list[str] = Field(default_factory=list)
    difficulty: str


class EvalRun(BaseModel):
    run_id: str
    dataset_id: str
    started_at: datetime
    completed_at: datetime
    results: list[EvalResult]
    summary: dict[str, float | int]
