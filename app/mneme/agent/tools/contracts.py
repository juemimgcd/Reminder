import json
from typing import Any

from pydantic import BaseModel, Field

from app.mneme.agent.contracts import AgentResponse
from app.mneme.agent.tools.base import ToolErrorKind


class BackendToolResult(BaseModel):
    tool_name: str
    answer: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: str
    uncertainty: str | None = None
    route: dict[str, Any] | None = None
    debug: dict[str, Any] | None = None
    is_error: bool = False
    error_kind: ToolErrorKind | None = None
    error_message: str | None = None

    @classmethod
    def from_agent_response(cls, tool_name: str, response: AgentResponse) -> "BackendToolResult":
        return cls(tool_name=tool_name, **response.model_dump(exclude={"tool_calls"}))

    @classmethod
    def success(
        cls,
        *,
        tool_name: str,
        evidence: dict[str, Any],
        fallback_answer: str,
        sources: list[dict[str, Any]] | None = None,
        confidence: str = "medium",
        uncertainty: str | None = None,
        route: dict[str, Any] | None = None,
        debug: dict[str, Any] | None = None,
    ) -> "BackendToolResult":
        return cls(
            tool_name=tool_name,
            answer=fallback_answer,
            evidence=evidence,
            sources=sources or [],
            confidence=confidence,
            uncertainty=uncertainty,
            route=route,
            debug=debug,
        )

    @classmethod
    def error(
        cls,
        *,
        tool_name: str,
        kind: ToolErrorKind,
        message: str,
    ) -> "BackendToolResult":
        return cls(
            tool_name=tool_name,
            answer="",
            confidence="low",
            uncertainty=message,
            is_error=True,
            error_kind=kind,
            error_message=message,
        )

    def to_model_text(self) -> str:
        payload = {
            "evidence": self.evidence,
            "sources": self.sources,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "is_error": self.is_error,
            "error_kind": self.error_kind,
            "error_message": self.error_message,
        }
        return json.dumps(payload, ensure_ascii=False)
