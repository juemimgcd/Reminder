import asyncio
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class AgentRunContext:
    db: AsyncSession
    user_id: int
    knowledge_base_id: str
    session_id: str | None
    llm_config: dict[str, Any] | None
    abort_signal: asyncio.Event

    def is_aborted(self) -> bool:
        return self.abort_signal.is_set()
