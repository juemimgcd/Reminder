from pydantic import BaseModel, Field


# 表达问答接口的输入请求结构。
class ChatQueryRequest(BaseModel):
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

    source_id: str
    knowledge_base_id: str | None = None
    document_id: str
    chunk_id: str
    page_no: int | None = None
    text: str



class ChatCitationItem(BaseModel):
    source_id: str = Field(..., description="稳定来源 ID，例如 S1")
    document_id: str = Field(..., description="来源文档 ID")
    chunk_id: str = Field(..., description="来源片段 ID")
    page_no: int | None = Field(default=None, description="来源页码")
    quote: str = Field(..., description="本次回答实际引用的证据片段")
    reason: str = Field(..., description="为什么它支撑当前回答")


class ChatQueryData(BaseModel):
    answer: str
    sources: list[ChatSourceItem]
    citations: list[ChatCitationItem]
    confidence: str
    uncertainty: str | None = None

class EvidenceCitationDraft(BaseModel):
    source_id: str = Field(..., description="模型引用的来源 ID")
    quote: str = Field(..., description="模型提取的证据片段")
    reason: str = Field(..., description="引用理由")


class EvidenceAnswerDraft(BaseModel):
    answer: str = Field(..., description="基于证据的最终回答")
    citations: list[EvidenceCitationDraft] = Field(default_factory=list)
    confidence: str = Field(..., description="high / medium / low")
    uncertainty: str | None = Field(default=None, description="仍不确定的部分")



from pydantic import BaseModel, Field


class ContextItem(BaseModel):
    recall_type: str = Field(..., description="vector / keyword / memory")
    score: float = Field(..., description="统一后的召回分数")
    knowledge_base_id: str | None = Field(default=None, description="知识库 ID")
    document_id: str = Field(..., description="来源文档 ID")
    chunk_id: str = Field(..., description="主 chunk ID")
    page_no: int | None = Field(default=None, description="主页码")
    text: str = Field(..., description="进入 prompt 的文本")
    source_chunk_ids: list[str] = Field(default_factory=list, description="合并后的源 chunk 列表")
    source_page_nos: list[int] = Field(default_factory=list, description="合并后的源页码列表")
    merged_chunk_count: int = Field(default=1, description="当前上下文块由多少个 chunk 合并而来")
    memory_entry_id: str | None = Field(default=None, description="如果来自 memory recall，对应的 entry id")
    entry_name: str | None = Field(default=None, description="命中的记忆条目名")
    matched_terms: list[str] = Field(default_factory=list, description="命中的关键词")