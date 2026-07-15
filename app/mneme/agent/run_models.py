from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel

from app.mneme.agent.contracts import AnswerMode
from app.mneme.agent.events import AgentEvent


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
    session_id: str
    user_id: int
    client_request_id: str = ""
    question: str
    top_k: int
    answer_mode: AnswerMode
    status: AgentRunStatus = AgentRunStatus.QUEUED
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    last_event_id: str | None = None
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
    ) -> "AgentRunRecord":
        return cls(
            run_id=run_id,
            session_id=session_id,
            user_id=user_id,
            client_request_id=client_request_id,
            question=question,
            top_k=top_k,
            answer_mode=answer_mode,
            created_at=datetime.now(timezone.utc),
        )


class AgentStoredEvent(BaseModel):
    event_id: str
    event: AgentEvent
