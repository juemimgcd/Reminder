import json
import math
from collections.abc import Sequence
from dataclasses import dataclass

from app.mneme.memoria.schemas.memory_agent import (
    ConversationContextData,
    ConversationMessageData,
    ConversationRole,
)
from app.mneme.models.chat_message import ChatMessage

MAX_MESSAGE_CONTENT_CHARS = 20_000


@dataclass(frozen=True)
class PreparedConversationContext:
    context: ConversationContextData
    persisted_summary: str
    persisted_summary_through_message_id: str | None
    before_tokens: int
    after_tokens: int
    compacted_messages: int
    compaction_reason: str | None


def prepare_conversation_context(
    messages: Sequence[ChatMessage],
    *,
    current_message_id: str,
    existing_summary: str,
    summary_through_message_id: str | None,
    max_messages: int,
    summary_max_chars: int,
    max_context_tokens: int | None = None,
    chars_per_token: float = 3.0,
    tool_result_soft_chars: int = 600,
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

    safe_chars_per_token = max(1.0, min(chars_per_token, 8.0))
    before_tokens = _estimate_text_tokens(
        existing_summary,
        safe_chars_per_token,
    ) + sum(
        _message_token_estimate(
            message,
            chars_per_token=safe_chars_per_token,
            tool_result_soft_chars=tool_result_soft_chars,
        )
        for message in unsummarized
    )
    recent_count = max(0, min(max_messages, 24))
    compacted = list(unsummarized[:-recent_count] if recent_count else unsummarized)
    recent = list(unsummarized[-recent_count:] if recent_count else [])
    compacted_for_turn_limit = len(compacted)

    token_budget = max(256, max_context_tokens or before_tokens or 256)
    effective_summary_max_chars = min(
        max(0, min(summary_max_chars, 20_000)),
        max(0, int(token_budget * safe_chars_per_token / 3)),
    )
    while recent and (
        _estimate_text_tokens(existing_summary, safe_chars_per_token)
        + sum(
            _message_token_estimate(
                message,
                chars_per_token=safe_chars_per_token,
                tool_result_soft_chars=tool_result_soft_chars,
            )
            for message in recent
        )
        > token_budget
    ):
        compacted.append(recent.pop(0))

    summary_entries = [_summary_entry(message) for message in compacted]
    persisted_summary = _bounded_summary(
        existing_summary,
        summary_entries,
        max_chars=effective_summary_max_chars,
    )
    while recent and (
        _estimate_text_tokens(persisted_summary, safe_chars_per_token)
        + sum(
            _estimate_text_tokens(message.content, safe_chars_per_token)
            for message in recent
        )
        > token_budget
    ):
        compacted.append(recent.pop(0))
        persisted_summary = _bounded_summary(
            existing_summary,
            [_summary_entry(message) for message in compacted],
            max_chars=effective_summary_max_chars,
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
    after_tokens = _estimate_text_tokens(
        persisted_summary,
        safe_chars_per_token,
    ) + sum(
        _estimate_text_tokens(message.content, safe_chars_per_token)
        for message in recent
    )
    token_compacted = len(compacted) > compacted_for_turn_limit
    reasons: list[str] = []
    if compacted_for_turn_limit:
        reasons.append("history_turn_limit")
    if token_compacted:
        reasons.append("context_window_pressure")
    return PreparedConversationContext(
        context=context,
        persisted_summary=persisted_summary,
        persisted_summary_through_message_id=persisted_watermark,
        before_tokens=before_tokens,
        after_tokens=after_tokens,
        compacted_messages=len(compacted),
        compaction_reason="+".join(reasons) or None,
    )


def _summary_entry(message: ChatMessage) -> str:
    role: ConversationRole = message.role
    label = "User" if role == "user" else "Assistant"
    content = " ".join(message.content.split())
    evidence_parts: list[str] = []
    if message.tool_calls_json:
        evidence_parts.append(f"tools={len(message.tool_calls_json)}")
    if message.sources_json:
        evidence_parts.append(f"sources={len(message.sources_json)}")
    evidence = f" [{', '.join(evidence_parts)}]" if evidence_parts else ""
    return f"{label}{evidence}: {content}"


def _message_token_estimate(
    message: ChatMessage,
    *,
    chars_per_token: float,
    tool_result_soft_chars: int,
) -> int:
    payload_chars = 0
    for payload in (message.tool_calls_json, message.sources_json):
        if payload:
            payload_chars += min(
                len(json.dumps(payload, ensure_ascii=False, default=str)),
                max(0, tool_result_soft_chars),
            )
    return _estimate_text_tokens(
        message.content + (" " * payload_chars),
        chars_per_token,
    )


def _estimate_text_tokens(value: str, chars_per_token: float) -> int:
    if not value:
        return 0
    return max(1, math.ceil(len(value) / chars_per_token))


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
