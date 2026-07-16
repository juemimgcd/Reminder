from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentEventType(str, Enum):
    LIFECYCLE = "lifecycle"
    ASSISTANT = "assistant"
    TOOL = "tool"
    COMPACTION = "compaction"
    ERROR = "error"


class AgentEvent(BaseModel):
    type: AgentEventType
    phase: str = ""
    content: str = ""
    tool: str = ""
    error: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_stream_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_defaults=True)

    @classmethod
    def lifecycle(cls, phase: str, **metadata: Any) -> "AgentEvent":
        return cls(type=AgentEventType.LIFECYCLE, phase=phase, metadata=metadata)

    @classmethod
    def assistant_delta(cls, content: str, **metadata: Any) -> "AgentEvent":
        return cls(type=AgentEventType.ASSISTANT, content=content, metadata=metadata)

    @classmethod
    def tool_event(cls, phase: str, tool: str, **metadata: Any) -> "AgentEvent":
        return cls(type=AgentEventType.TOOL, phase=phase, tool=tool, metadata=metadata)

    @classmethod
    def compaction(cls, phase: str, **metadata: Any) -> "AgentEvent":
        return cls(type=AgentEventType.COMPACTION, phase=phase, metadata=metadata)

    @classmethod
    def error_event(cls, error: str, **metadata: Any) -> "AgentEvent":
        return cls(type=AgentEventType.ERROR, phase="error", error=error, metadata=metadata)
