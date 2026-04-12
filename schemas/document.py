from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadData(BaseModel):
    document_id: str = Field(..., description="上传成功后的文档 ID")
    user_id: int = Field(..., description="所属用户 ID")
    knowledge_base_id: str | None = Field(..., description="所属知识库 ID")
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



class DocumentListData(BaseModel):
    items: list[DocumentListItem]
    total: int



class DocumentIndexData(BaseModel):
    document_id: str
    knowledge_base_id: str
    chunk_count: int
    status: str





