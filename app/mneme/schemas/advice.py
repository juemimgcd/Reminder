from pydantic import BaseModel, Field


class GrowthAdviceRequest(BaseModel):
    focus_goal: str | None = Field(default=None, description="可选，希望优先关注的目标")


class ActionSuggestionItem(BaseModel):
    area: str = Field(..., description="建议领域")
    why_now: str = Field(..., description="为什么当前阶段适合做这件事")
    action: str = Field(..., description="建议动作")
    first_step: str = Field(..., description="最小第一步")
    evidence_entries: list[str] = Field(default_factory=list, description="支撑这条建议的词条名")


class GrowthAdviceResult(BaseModel):
    knowledge_base_id: str = Field(..., description="所属知识库")
    focus_goal: str | None = Field(default=None, description="可选目标")
    advice_summary: str = Field(..., description="建议摘要")
    current_priorities: list[str] = Field(default_factory=list, description="当前优先级")
    action_suggestions: list[ActionSuggestionItem] = Field(default_factory=list)
    avoid_list: list[str] = Field(default_factory=list, description="当前不建议分散精力的方向")
    one_week_plan: list[str] = Field(default_factory=list, description="未来一周的建议动作")
    reflection_questions: list[str] = Field(default_factory=list, description="帮助继续复盘的问题")