from datetime import datetime

from pydantic import BaseModel, Field


class ProfileEvidenceItem(BaseModel):
    entry_id: str
    entry_name: str
    entry_type: str
    summary: str
    evidence_text: str
    document_id: str
    chunk_id: str
    created_at: datetime


class ProfileToolCallItem(BaseModel):
    tool_name: str
    input: dict
    output_count: int
    evidence_entry_ids: list[str] = Field(default_factory=list)


class EvidenceProfileTraitItem(BaseModel):
    trait_name: str
    summary: str
    confidence: str
    evidence_entry_ids: list[str] = Field(default_factory=list)


class EvidenceProfileRiskItem(BaseModel):
    risk_name: str
    summary: str
    relation_type: str
    evidence_entry_ids: list[str] = Field(default_factory=list)


class TopicTimelineItem(BaseModel):
    topic_name: str
    entry_type: str
    entry_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    evidence_entry_ids: list[str] = Field(default_factory=list)


class EvidenceProfileData(BaseModel):
    knowledge_base_id: str
    entry_count: int
    canonical_memory_count: int
    stable_traits: list[EvidenceProfileTraitItem] = Field(default_factory=list)
    recent_focus: list[EvidenceProfileTraitItem] = Field(default_factory=list)
    goals: list[EvidenceProfileTraitItem] = Field(default_factory=list)
    risks: list[EvidenceProfileRiskItem] = Field(default_factory=list)
    topic_timeline: list[TopicTimelineItem] = Field(default_factory=list)
    evidence: list[ProfileEvidenceItem] = Field(default_factory=list)
    tool_calls: list[ProfileToolCallItem] = Field(default_factory=list)
    uncertainty: str | None = None
