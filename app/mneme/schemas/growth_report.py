from pydantic import BaseModel, Field


class ThemeChangeItem(BaseModel):
    theme_name: str = Field(..., description="主题名")
    change_type: str = Field(..., description="new、stronger、weaker、stable")
    reason: str = Field(..., description="变化判断依据")
    evidence_entries: list[str] = Field(default_factory=list, description="支撑变化的词条名")


class GrowthReportResult(BaseModel):
    knowledge_base_id: str = Field(..., description="所属知识库")
    analysis_window: str = Field(..., description="分析窗口说明")
    stage_summary: str = Field(..., description="阶段总结")
    recent_focus: list[str] = Field(default_factory=list, description="最近关注主题")
    theme_changes: list[ThemeChangeItem] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list, description="阶段亮点")
    blockers: list[str] = Field(default_factory=list, description="当前卡点")
    next_actions: list[str] = Field(default_factory=list, description="下一步建议")