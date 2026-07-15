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
        history.append(
            AgentHistoryMessage(
                message_id=str(getattr(message, "id", "") or "") or None,
                role=role,
                content=content,
                tool_calls=list(getattr(message, "tool_calls_json", None) or []),
                sources=list(getattr(message, "sources_json", None) or []),
                citations=list(getattr(message, "citations_json", None) or []),
            )
        )
    return history
