from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadData(BaseModel):
    document_id: str = Field(..., description="Document ID after upload")
    user_id: int = Field(..., description="Owner user ID")
    knowledge_base_id: str | None = Field(..., description="Knowledge base ID")
    file_name: str
    file_type: str
    file_size: int
    status: str


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    knowledge_base_id: str
    file_name: str
    file_type: str
    status: str
    created_at: datetime


class DocumentDetailItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    knowledge_base_id: str
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentPreviewChunk(BaseModel):
    chunk_id: str
    chunk_index: int
    text: str
    page_no: int | None
    section_title: str | None


class DocumentPreviewMemoryEntry(BaseModel):
    entry_id: str
    entry_name: str
    entry_type: str
    summary: str
    importance_score: float


class DocumentPreviewData(BaseModel):
    document_id: str
    knowledge_base_id: str
    file_name: str
    file_type: str
    status: str
    summary: str
    chunks: list[DocumentPreviewChunk]
    memory_entries: list[DocumentPreviewMemoryEntry]


class DocumentListData(BaseModel):
    items: list[DocumentListItem]
    total: int


class DocumentIndexData(BaseModel):
    document_id: str
    knowledge_base_id: str
    chunk_count: int
    status: str


class DocumentIndexTaskData(BaseModel):
    task_id: str = Field(..., description="Index task ID")
    document_id: str = Field(..., description="Document ID")
    knowledge_base_id: str = Field(..., description="Knowledge base ID")
    status: str = Field(..., description="Current task status")
    message: str = Field(default="index task submitted", description="Submission message")


class DocumentIndexPipelineResult(BaseModel):
    document_id: str
    knowledge_base_id: str
    chunk_count: int
    section_count: int
    deleted_memory_entry_count: int
    memory_entry_count: int
    vector_batch_count: int
    vector_batch_size: int
    indexed_vector_count: int
    status: str


class DocumentDeleteData(BaseModel):
    document_id: str
    knowledge_base_id: str
    chunk_count: int
    deleted_memory_entry_count: int
    deleted_task_count: int
    deleted_vector_count: int


class DocumentFolderCreate(BaseModel):
    knowledge_base_id: str
    parent_id: str
    name: str = Field(min_length=1, max_length=255)


class DocumentFolderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: str | None = None


class DocumentFolderItem(BaseModel):
    id: str
    parent_id: str
    name: str
    is_root: bool
    children: list["DocumentFolderItem"] = Field(default_factory=list)


class DocumentMoveRequest(BaseModel):
    folder_id: str
