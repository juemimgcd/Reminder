from pydantic import BaseModel, Field


# 表达问答接口的输入请求结构。
class ChatQueryRequest(BaseModel):
    user_id: int = Field(..., description="用户 ID")
    question: str = Field(..., description="用户输入的问题")
    knowledge_base_id: str = Field(..., description="知识库 ID")
    top_k: int = Field(default=4, ge=1, le=10, description="检索返回的片段数量")
    session_id: str | None = Field(default=None, description="可选，会话 ID")


# 表达问答接口里单条引用来源的结构。
class ChatSourceItem(BaseModel):
    # source item 结构示例：
    # {
    #     "knowledge_base_id": "kb_demo_001",
    #     "document_id": "doc_demo_001",
    #     "chunk_id": "doc_demo_001_chunk_0_a1b2c3",
    #     "page_no": 1,
    #     "text": "这是一段被引用的上下文文本",
    # }
    knowledge_base_id: str | None = None
    document_id: str
    chunk_id: str
    page_no: int | None = None
    text: str


# 表达问答接口的最终响应数据结构。
class ChatQueryData(BaseModel):
    answer: str
    sources: list[ChatSourceItem]
