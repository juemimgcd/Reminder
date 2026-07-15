import asyncio
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.agent.runtime_events import RuntimeEventDispatcher


@dataclass(frozen=True)
class AgentRunContext:
    db: AsyncSession
    user_id: int
    knowledge_base_id: str
    session_id: str | None
    run_id: str | None
    trace_id: str
    llm_config: dict[str, Any] | None
    abort_signal: asyncio.Event
    runtime_events: RuntimeEventDispatcher

    def is_aborted(self) -> bool:
        return self.abort_signal.is_set()
