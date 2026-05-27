from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.mneme.schemas.eval import RetrievalEvalMetrics


class GraphRagSeedItem(BaseModel):
    entry_id: str
    entry_name: str
    entry_type: str
    summary: str
    document_id: str
    chunk_id: str
    matched_terms: list[str] = Field(default_factory=list)
    score: float
    importance_score: float
    created_at: datetime


class GraphRagExpansionItem(BaseModel):
    edge_id: str
    source_document_id: str
    target_document_id: str
    source_document_name: str | None = None
    target_document_name: str | None = None
    relationship_score: float
    shared_memory_count: int
    shared_memories: list[dict[str, Any]] = Field(default_factory=list)
    evidence_entry_ids: list[str] = Field(default_factory=list)
    relationship_rank: int | None = None


class GraphRagContextItem(BaseModel):
    context_id: str
    context_type: str
    document_id: str
    document_name: str | None = None
    chunk_id: str | None = None
    memory_entry_ids: list[str] = Field(default_factory=list)
    score: float
    reason: str
    text: str


class GraphRagDecisionData(BaseModel):
    knowledge_base_id: str
    query: str
    query_terms: list[str] = Field(default_factory=list)
    graph_useful: bool
    reason: str
    seed_count: int
    expansion_count: int
    context_count: int
    generated_at: datetime
    seeds: list[GraphRagSeedItem] = Field(default_factory=list)
    expansions: list[GraphRagExpansionItem] = Field(default_factory=list)
    contexts: list[GraphRagContextItem] = Field(default_factory=list)


class GraphRagEvalComparisonData(BaseModel):
    query: str
    expected_source_chunk_ids: list[str] = Field(default_factory=list)
    baseline_chunk_ids: list[str] = Field(default_factory=list)
    graph_chunk_ids: list[str] = Field(default_factory=list)
    baseline: RetrievalEvalMetrics
    graph: RetrievalEvalMetrics
    delta: dict[str, float] = Field(default_factory=dict)
