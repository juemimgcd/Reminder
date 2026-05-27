from pydantic import BaseModel, Field


class CompanionQueryRequest(BaseModel):
    question: str = Field(..., description="用户问题")
    top_k: int = Field(default=4, ge=1, le=10, description="检索片段数量")


class CompanionCitationItem(BaseModel):
    document_id: str = Field(..., description="来源文档 ID")
    chunk_id: str = Field(..., description="来源片段 ID")
    page_no: int | None = Field(default=None, description="页码")
    text: str = Field(..., description="引用片段文本")
    reason: str = Field(..., description="为什么这个片段支撑当前回答")


class CompanionAnswerResult(BaseModel):
    knowledge_base_id: str = Field(..., description="所属知识库")
    question: str = Field(..., description="用户问题")
    direct_answer: str = Field(..., description="直接回答")
    citations: list[CompanionCitationItem] = Field(default_factory=list)
    profile_snapshot: str = Field(..., description="长期画像摘要")
    growth_snapshot: str = Field(..., description="最近阶段摘要")
    next_step_hint: str = Field(..., description="最建议的下一步")
    follow_up_questions: list[str] = Field(default_factory=list, description="推荐继续追问的问题")
    companion_message: str = Field(..., description="更像产品输出的陪伴式总结")