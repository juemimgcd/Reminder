from pydantic import BaseModel, Field


class MemoryEntryExtractItem(BaseModel):
    entry_name: str = Field(..., description="词条名称")
    entry_type: str = Field(..., description="词条类型")
    summary: str = Field(..., description="词条简述")
    evidence_text: str = Field(..., description="支撑这条词条的原文证据")
    importance_score: float = Field(default=0.5, description="重要性分数，0 到 1")


class MemoryEntryExtractionResult(BaseModel):
    entries: list[MemoryEntryExtractItem]