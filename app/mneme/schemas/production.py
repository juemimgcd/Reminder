from pydantic import BaseModel, Field


class ReadinessCheckData(BaseModel):
    name: str
    status: str = Field(..., description="pass, warn, or fail")
    reason: str


class FrameworkDecisionData(BaseModel):
    area: str
    decision: str = Field(..., description="keep_self_built, optional_poc, or avoid_by_default")
    reason: str


class ProductionReadinessReportData(BaseModel):
    overall_status: str
    checks: list[ReadinessCheckData] = Field(default_factory=list)
    framework_decisions: list[FrameworkDecisionData] = Field(default_factory=list)
    default_stack: list[str] = Field(default_factory=list)
    optional_stack: list[str] = Field(default_factory=list)
    avoid_by_default: list[str] = Field(default_factory=list)
    markdown: str
