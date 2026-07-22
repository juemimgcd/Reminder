from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class AgentEventType(str, Enum):
    LIFECYCLE = "lifecycle"
    ASSISTANT = "assistant"
    TOOL = "tool"
    COMPACTION = "compaction"
    ERROR = "error"


class AgentRunEventType(str, Enum):
    RUN_QUEUED = "run.queued"
    RUN_STARTED = "run.started"
    RUN_CONTROL_ACCEPTED = "run.control.accepted"
    QUERY_REWRITTEN = "query.rewritten"
    RETRIEVAL_STARTED = "retrieval.started"
    RETRIEVAL_SOURCE_COMPLETED = "retrieval.source_completed"
    EVIDENCE_SELECTED = "evidence.selected"
    MULTI_AGENT_COORDINATOR_COMPLETED = "multi_agent.coordinator.completed"
    MULTI_AGENT_ROLE_STARTED = "multi_agent.role.started"
    MULTI_AGENT_ROLE_COMPLETED = "multi_agent.role.completed"
    MULTI_AGENT_ROLE_FAILED = "multi_agent.role.failed"
    MULTI_AGENT_JUDGE_COMPLETED = "multi_agent.judge.completed"
    ANSWER_STARTED = "answer.started"
    ANSWER_DELTA = "answer.delta"
    CITATION_RESOLVED = "citation.resolved"
    GROUNDING_DECIDED = "grounding.decided"
    ANSWER_COMPLETED = "answer.completed"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    CONTEXT_COMPACTED = "context.compacted"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"


class AgentEvent(BaseModel):
    type: AgentEventType
    name: AgentRunEventType | None = None
    schema_version: str = "2"
    run_id: str | None = None
    sequence: int | None = Field(default=None, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_role: str = "memory_agent"
    phase: str = ""
    content: str = ""
    tool: str = ""
    error: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def resolve_canonical_name(self) -> "AgentEvent":
        if self.name is None:
            self.name = _legacy_event_name(self.type, self.phase)
        return self

    def to_stream_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True, exclude_defaults=True)

    def with_delivery(self, *, run_id: str, sequence: int) -> "AgentEvent":
        return self.model_copy(
            update={
                "run_id": run_id,
                "sequence": sequence,
                "created_at": datetime.now(timezone.utc),
            }
        )

    @classmethod
    def lifecycle(cls, phase: str, **metadata: Any) -> "AgentEvent":
        run_id = _pop_optional_string(metadata, "run_id")
        return cls(
            type=AgentEventType.LIFECYCLE,
            name=_legacy_event_name(AgentEventType.LIFECYCLE, phase),
            run_id=run_id,
            phase=phase,
            metadata=metadata,
        )

    @classmethod
    def assistant_delta(cls, content: str, **metadata: Any) -> "AgentEvent":
        run_id = _pop_optional_string(metadata, "run_id")
        return cls(
            type=AgentEventType.ASSISTANT,
            name=AgentRunEventType.ANSWER_DELTA,
            run_id=run_id,
            phase="stream",
            content=content,
            metadata=metadata,
        )

    @classmethod
    def tool_event(cls, phase: str, tool: str, **metadata: Any) -> "AgentEvent":
        run_id = _pop_optional_string(metadata, "run_id")
        return cls(
            type=AgentEventType.TOOL,
            name=(
                AgentRunEventType.TOOL_STARTED
                if phase in {"start", "started"}
                else AgentRunEventType.TOOL_COMPLETED
            ),
            run_id=run_id,
            phase=phase,
            tool=tool,
            metadata=metadata,
        )

    @classmethod
    def compaction(cls, phase: str, **metadata: Any) -> "AgentEvent":
        run_id = _pop_optional_string(metadata, "run_id")
        return cls(
            type=AgentEventType.COMPACTION,
            name=AgentRunEventType.CONTEXT_COMPACTED,
            run_id=run_id,
            phase=phase,
            metadata=metadata,
        )

    @classmethod
    def error_event(cls, error: str, **metadata: Any) -> "AgentEvent":
        run_id = _pop_optional_string(metadata, "run_id")
        return cls(
            type=AgentEventType.ERROR,
            name=AgentRunEventType.RUN_FAILED,
            run_id=run_id,
            phase="error",
            error=error,
            metadata=metadata,
        )

    @classmethod
    def rag_progress(
        cls,
        name: AgentRunEventType,
        *,
        phase: str,
        run_id: str | None = None,
        **metadata: Any,
    ) -> "AgentEvent":
        agent_role = _pop_optional_string(metadata, "agent_role") or "memory_agent"
        return cls(
            type=AgentEventType.LIFECYCLE,
            name=name,
            run_id=run_id,
            phase=phase,
            agent_role=agent_role,
            metadata=metadata,
        )


def _legacy_event_name(event_type: AgentEventType, phase: str) -> AgentRunEventType:
    if event_type == AgentEventType.ASSISTANT:
        return AgentRunEventType.ANSWER_DELTA
    if event_type == AgentEventType.TOOL:
        return (
            AgentRunEventType.TOOL_STARTED
            if phase in {"start", "started"}
            else AgentRunEventType.TOOL_COMPLETED
        )
    if event_type == AgentEventType.COMPACTION:
        return AgentRunEventType.CONTEXT_COMPACTED
    if event_type == AgentEventType.ERROR or phase == "error":
        return AgentRunEventType.RUN_FAILED
    if phase in {"aborted", "cancelled"}:
        return AgentRunEventType.RUN_CANCELLED
    if phase == "queued":
        return AgentRunEventType.RUN_QUEUED
    if phase == "start":
        return AgentRunEventType.RUN_STARTED
    if phase == "end":
        return AgentRunEventType.ANSWER_COMPLETED
    if phase.endswith("retrieve") or phase.endswith("retrieve_started"):
        return AgentRunEventType.RETRIEVAL_STARTED
    if phase.endswith("retrieve_completed"):
        return AgentRunEventType.RETRIEVAL_SOURCE_COMPLETED
    if phase.endswith("generate") or phase.endswith("generate_started"):
        return AgentRunEventType.ANSWER_STARTED
    if phase.endswith("citations") or phase.endswith("citations_completed"):
        return AgentRunEventType.CITATION_RESOLVED
    if phase.endswith("grounding") or phase.endswith("grounding_completed"):
        return AgentRunEventType.GROUNDING_DECIDED
    return AgentRunEventType.RUN_STARTED


def _pop_optional_string(values: dict[str, Any], key: str) -> str | None:
    value = values.pop(key, None)
    return value if isinstance(value, str) and value else None
