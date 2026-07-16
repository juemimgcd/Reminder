from collections.abc import Sequence
from dataclasses import dataclass

from app.mneme.models.chat_message import ChatMessage
from app.mneme.schemas.memory_agent import (
    ConversationContextData,
    ConversationMessageData,
    ConversationRole,
)

MAX_MESSAGE_CONTENT_CHARS = 20_000


@dataclass(frozen=True)
class PreparedConversationContext:
    context: ConversationContextData
    persisted_summary: str
    persisted_summary_through_message_id: str | None


def prepare_conversation_context(
    messages: Sequence[ChatMessage],
    *,
    current_message_id: str,
    existing_summary: str,
    summary_through_message_id: str | None,
    max_messages: int,
    summary_max_chars: int,
) -> PreparedConversationContext:
    eligible = [
        message
        for message in messages
        if message.id != current_message_id
        and message.role in {"user", "assistant"}
        and message.content.strip()
    ]
    unsummarized = eligible
    if summary_through_message_id is not None:
        watermark_index = next(
            (
                index
                for index, message in enumerate(eligible)
                if message.id == summary_through_message_id
            ),
            None,
        )
        if watermark_index is not None:
            unsummarized = eligible[watermark_index + 1 :]

    recent_count = max(0, min(max_messages, 24))
    compacted = unsummarized[:-recent_count] if recent_count else unsummarized
    recent = unsummarized[-recent_count:] if recent_count else []

    summary_entries = [_summary_entry(message) for message in compacted]
    persisted_summary = _bounded_summary(
        existing_summary,
        summary_entries,
        max_chars=max(0, min(summary_max_chars, 20_000)),
    )
    persisted_watermark = (
        compacted[-1].id if compacted else summary_through_message_id
    )
    context = ConversationContextData(
        summary=persisted_summary,
        summary_through_message_id=persisted_watermark,
        messages=[
            ConversationMessageData(
                message_id=message.id,
                role=message.role,
                content=message.content.strip()[:MAX_MESSAGE_CONTENT_CHARS],
            )
            for message in recent
        ],
    )
    return PreparedConversationContext(
        context=context,
        persisted_summary=persisted_summary,
        persisted_summary_through_message_id=persisted_watermark,
    )


def _summary_entry(message: ChatMessage) -> str:
    role: ConversationRole = message.role
    label = "User" if role == "user" else "Assistant"
    content = " ".join(message.content.split())
    return f"{label}: {content}"


def _bounded_summary(existing: str, entries: list[str], *, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    combined = "\n".join(part for part in (existing.strip(), *entries) if part)
    if len(combined) <= max_chars:
        return combined

    selected: list[str] = []
    used = 0
    for line in reversed(combined.splitlines()):
        separator = 1 if selected else 0
        if len(line) + separator + used <= max_chars:
            selected.append(line)
            used += len(line) + separator
            continue
        if not selected:
            selected.append(line[-max_chars:])
        break
    return "\n".join(reversed(selected))
