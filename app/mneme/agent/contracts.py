from typing import Any

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    question: str
    knowledge_base_id: str = Field(..., min_length=1)
    user_id: int
    top_k: int = Field(default=4, ge=1, le=10)
    llm_config: dict[str, Any] | None = None


class AgentResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: str
    uncertainty: str | None = None
    route: dict[str, Any] | None = None
    debug: dict[str, Any] | None = None

    def to_legacy_result(self) -> dict[str, Any]:
        return self.model_dump()
