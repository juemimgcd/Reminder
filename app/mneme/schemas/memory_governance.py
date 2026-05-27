from datetime import datetime

from pydantic import BaseModel, Field


class CanonicalMemoryItem(BaseModel):
    canonical_id: str
    entry_name: str
    entry_type: str
    summary: str
    representative_entry_id: str
    entry_ids: list[str]
    evidence_count: int
    document_count: int
    importance_score: float
    status: str = Field(..., description="single / stable / merged / needs_review")
    first_seen_at: datetime
    last_seen_at: datetime


class MemoryRelationItem(BaseModel):
    relation_id: str
    source_entry_id: str
    target_entry_id: str
    relation_type: str = Field(
        ...,
        description="duplicate / supplement / contradict / refine / temporal_update",
    )
    confidence: float
    reason: str


class MemoryGovernanceData(BaseModel):
    knowledge_base_id: str
    raw_entry_count: int
    canonical_memory_count: int
    relation_count: int
    relation_type_counts: dict[str, int]
    canonical_memories: list[CanonicalMemoryItem]
    relations: list[MemoryRelationItem]
