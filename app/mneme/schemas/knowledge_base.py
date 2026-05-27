from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="知识库名称")
    description: str | None = Field(default=None, description="知识库描述")


class KnowledgeBaseData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    name: str
    description: str | None = None
    is_default: bool
    created_at: datetime


class KnowledgeBaseListData(BaseModel):
    items: list[KnowledgeBaseData]
    total: int


class KnowledgeBaseDeleteData(BaseModel):
    knowledge_base_id: str
    document_count: int
    chunk_count: int
    deleted_memory_entry_count: int
    deleted_task_count: int
    deleted_vector_count: int
