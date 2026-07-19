from datetime import datetime

from pydantic import BaseModel


class MemoryTimelineItem(BaseModel):
    entry_id: str
    entry_name: str
    entry_type: str
    summary: str
    created_at: datetime


class MemoryThemeItem(BaseModel):
    theme_name: str
    entries: list[str]
    count: int


class MemoryLibraryData(BaseModel):
    timeline: list[MemoryTimelineItem]
    by_type: dict[str, list[str]]
    by_theme: list[MemoryThemeItem]


class MemoryRebuildData(BaseModel):
    knowledge_base_id: str
    document_count: int
    processed_document_count: int
    chunk_count: int
    deleted_entry_count: int
    entry_count: int
