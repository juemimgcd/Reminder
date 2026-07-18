import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from app.mneme.memoria.contracts import AnswerMode
from app.mneme.memoria.events import AgentEvent


class AgentRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTING = "aborting"
    ABORTED = "aborted"


TERMINAL_AGENT_RUN_STATUSES = {
    AgentRunStatus.COMPLETED,
    AgentRunStatus.FAILED,
    AgentRunStatus.ABORTED,
}


class AgentRunRecord(BaseModel):
    run_id: str
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid.uuid4().hex}")
    session_id: str
    user_id: int
    client_request_id: str = ""
    question: str
    top_k: int
    answer_mode: AnswerMode
    status: AgentRunStatus = AgentRunStatus.QUEUED
    trigger_type: str = "user"
    trigger_id: str | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    last_event_id: str | None = None
    last_event_sequence: int = Field(default=0, ge=0)
    queue_wait_ms: int | None = None

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        session_id: str,
        user_id: int,
        client_request_id: str,
        question: str,
        top_k: int,
        answer_mode: AnswerMode,
        trigger_type: str = "user",
        trigger_id: str | None = None,
        max_attempts: int = 3,
    ) -> "AgentRunRecord":
        return cls(
            run_id=run_id,
            trace_id=f"trace_{uuid.uuid4().hex}",
            session_id=session_id,
            user_id=user_id,
            client_request_id=client_request_id,
            question=question,
            top_k=top_k,
            answer_mode=answer_mode,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            max_attempts=max_attempts,
            created_at=datetime.now(timezone.utc),
        )


class AgentStoredEvent(BaseModel):
    event_id: str
    event: AgentEvent
