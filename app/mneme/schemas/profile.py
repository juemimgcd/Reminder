from pydantic import BaseModel, Field


class ProfileThemeItem(BaseModel):
    theme_name: str = Field(..., description="长期主题")
    reason: str = Field(..., description="主题判断依据")
    evidence_entries: list[str] = Field(default_factory=list, description="支撑主题的词条名")


class AbilityTagItem(BaseModel):
    ability_name: str = Field(..., description="能力标签")
    reason: str = Field(..., description="能力判断依据")
    evidence_entries: list[str] = Field(default_factory=list, description="支撑能力的词条名")


class PersonalProfileResult(BaseModel):
    knowledge_base_id: str = Field(..., description="画像所属知识库")
    entry_count: int = Field(..., description="本次画像使用的词条数")
    profile_summary: str = Field(..., description="画像摘要")
    main_themes: list[ProfileThemeItem] = Field(default_factory=list)
    ability_tags: list[AbilityTagItem] = Field(default_factory=list)
    expression_style: str = Field(..., description="表达风格总结")
    growth_focus: list[str] = Field(default_factory=list, description="稳定关注点")