from collections.abc import Iterable
from typing import Any

from app.mneme.agent.contracts import AgentHistoryMessage


def build_agent_history(messages: Iterable[Any]) -> list[AgentHistoryMessage]:
    history: list[AgentHistoryMessage] = []
    for message in messages:
        role = str(getattr(message, "role", ""))
        content = str(getattr(message, "content", "") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        history.append(AgentHistoryMessage(role=role, content=content))
    return history
