from pydantic import BaseModel, Field


class MemoryEntryExtractItem(BaseModel):
    entry_name: str = Field(..., description="词条名称")
    entry_type: str = Field(..., description="词条类型")
    summary: str = Field(..., description="词条简述")
    evidence_text: str = Field(..., description="支撑这条词条的原文证据")
    importance_score: float = Field(default=0.5, description="重要性分数，0 到 1")


class MemoryEntryExtractionResult(BaseModel):
    entries: list[MemoryEntryExtractItem]




class MemoryEntryPayload(BaseModel):
    id: str
    user_id: int
    knowledge_base_id: str
    knowledge_base_pk: int
    document_id: str
    document_pk: int
    chunk_id: str
    page_no: int | None = None
    entry_name: str
    entry_type: str
    summary: str
    evidence_text: str
    importance_score: float


class MemoryExtractPipelineResult(BaseModel):
    knowledge_base_id: str
    document_id: str | None = None
    raw_entry_count: int
    dedup_entry_count: int
    persisted_entry_count: int