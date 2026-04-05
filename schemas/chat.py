from pydantic import BaseModel, Field


class ChatQueryRequest(BaseModel):
    user_id: int = Field(..., description="用户 ID")
    question: str = Field(..., description="用户输入的问题")
    knowledge_base_id: str = Field(..., description="知识库 ID")
    top_k: int = Field(default=4, ge=1, le=10, description="检索返回的片段数量")
    session_id: str | None = Field(default=None, description="可选，会话 ID")


class ChatSourceItem(BaseModel):
    knowledge_base_id: str | None = None
    document_id: str
    chunk_id: str
    page_no: int | None = None
    text: str


class ChatQueryData(BaseModel):
    answer: str
    sources: list[ChatSourceItem]
