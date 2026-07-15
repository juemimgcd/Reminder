from typing import Any, Literal

from pydantic import BaseModel, Field

AnswerMode = Literal["kb_qa", "memory_query", "profile_query", "analysis_query", "general_chat"]


class AgentHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AgentRequest(BaseModel):
    question: str
    knowledge_base_id: str = Field(..., min_length=1)
    user_id: int
    session_id: str | None = None
    top_k: int = Field(default=4, ge=1, le=10)
    answer_mode: AnswerMode = "kb_qa"
    llm_config: dict[str, Any] | None = None
    history: list[AgentHistoryMessage] = Field(default_factory=list)


class AgentResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: str
    uncertainty: str | None = None
    route: dict[str, Any] | None = None
    debug: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)

    def to_legacy_result(self) -> dict[str, Any]:
        return self.model_dump()
