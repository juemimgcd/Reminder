from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# 表达上传接口成功返回的最小文档信息。
class DocumentUploadData(BaseModel):
    document_id: str = Field(..., description="上传成功后的文档 ID")
    user_id: int = Field(..., description="所属用户 ID")
    knowledge_base_id: str | None = Field(..., description="所属知识库 ID")
    file_name: str
    file_type: str
    file_size: int
    status: str


# 表达文档列表接口中的单条文档摘要。
class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    knowledge_base_id: str
    file_name: str
    file_type: str
    status: str
    created_at: datetime


# 表达文档详情接口中的单条完整文档信息。
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


# 表达文档列表接口的聚合返回结构。
class DocumentListData(BaseModel):
    items: list[DocumentListItem]
    total: int


# 表达文档索引完成后返回的最小结果摘要。
class DocumentIndexData(BaseModel):
    document_id: str
    knowledge_base_id: str
    chunk_count: int
    status: str


# 表达文档索引任务提交成功后的任务信息。
class DocumentIndexTaskData(BaseModel):
    task_id: str = Field(..., description="索引任务 ID")
    document_id: str = Field(..., description="文档 ID")
    knowledge_base_id: str = Field(..., description="知识库 ID")
    status: str = Field(..., description="任务当前状态")
    message: str = Field(default="index task submitted", description="任务提交说明")



class DocumentIndexPipelineResult(BaseModel):
    document_id: str
    knowledge_base_id: str
    chunk_count: int
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
