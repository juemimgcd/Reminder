from datetime import datetime

from pydantic import BaseModel, Field


class StatusCountData(BaseModel):
    name: str
    count: int


class BackendStatusData(BaseModel):
    backend: str
    status_counts: list[StatusCountData] = Field(default_factory=list)
    total: int


class DocumentAnalyticsData(BaseModel):
    document_count: int
    total_file_size: int
    status_counts: list[StatusCountData] = Field(default_factory=list)


class ChunkAnalyticsData(BaseModel):
    chunk_count: int
    avg_chunks_per_document: float
    section_count: int


class MemoryAnalyticsData(BaseModel):
    memory_entry_count: int
    entry_type_counts: list[StatusCountData] = Field(default_factory=list)


class TaskAnalyticsData(BaseModel):
    task_count: int
    active_task_count: int
    failed_task_count: int
    status_counts: list[StatusCountData] = Field(default_factory=list)


class OutboxAnalyticsData(BaseModel):
    event_count: int
    failed_event_count: int
    dead_letter_count: int
    backend_status: list[BackendStatusData] = Field(default_factory=list)


class KnowledgeBaseAnalyticsReportData(BaseModel):
    knowledge_base_id: str
    generated_at: datetime
    documents: DocumentAnalyticsData
    chunks: ChunkAnalyticsData
    memory: MemoryAnalyticsData
    tasks: TaskAnalyticsData
    outbox: OutboxAnalyticsData
    markdown: str
