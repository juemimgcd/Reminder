import json
import math
from dataclasses import dataclass

from app.mneme.agent.contracts import AgentHistoryMessage


@dataclass(frozen=True)
class HistoryBudgetResult:
    messages: list[AgentHistoryMessage]
    summary: str
    summary_through_message_id: str | None
    original_count: int
    kept_count: int
    original_chars: int
    kept_chars: int
    estimated_tokens_before: int
    estimated_tokens_after: int
    tool_payloads_trimmed: int
    reason: str

    @property
    def was_compacted(self) -> bool:
        return self.kept_count < self.original_count or self.tool_payloads_trimmed > 0


def apply_history_budget(
    history: list[AgentHistoryMessage],
    *,
    context_window_tokens: int = 64_000,
    output_reserve_tokens: int = 4096,
    system_chars: int = 0,
    current_question_chars: int = 0,
    max_turns: int = 12,
    summary_max_chars: int = 2000,
    chars_per_token: float = 3.0,
    tool_result_soft_chars: int = 600,
) -> HistoryBudgetResult:
    original_chars = sum(_message_chars(item) for item in history)
    protected_chars = system_chars + current_question_chars
    available_tokens = max(
        0,
        context_window_tokens - output_reserve_tokens - _estimate_tokens(protected_chars, chars_per_token),
    )
    max_history_chars = int(available_tokens * chars_per_token)
    max_messages = max(2, max_turns * 2)
    kept = [item.model_copy(deep=True) for item in history[-max_messages:]]
    reasons: list[str] = []
    if len(kept) < len(history):
        reasons.append("turn_limit")

    trimmed_count = 0
    if sum(_message_chars(item) for item in kept) > max_history_chars:
        trimmed_count = _soft_trim_tool_payloads(
            kept,
            tool_result_soft_chars,
            max_history_chars,
        )
        if trimmed_count:
            reasons.append("tool_payload_soft_trim")

    if sum(_message_chars(item) for item in kept) > max_history_chars:
        hard_trimmed = _hard_clear_tool_payloads(kept, max_history_chars)
        trimmed_count += hard_trimmed
        if hard_trimmed:
            reasons.append("tool_payload_hard_clear")

    # Natural-language messages are removed only after raw tool payloads have
    # been reduced. The newest user/assistant pair remains intact.
    while len(kept) > 2 and sum(_message_chars(item) for item in kept) > max_history_chars:
        kept.pop(0)
        if "context_window_budget" not in reasons:
            reasons.append("context_window_budget")

    removed_count = len(history) - len(kept)
    removed = history[:removed_count]
    summary = _summarize_removed_messages(removed, summary_max_chars)
    kept_chars = sum(_message_chars(item) for item in kept)
    summary_chars = len(summary)
    return HistoryBudgetResult(
        messages=kept,
        summary=summary,
        summary_through_message_id=removed[-1].message_id if removed else None,
        original_count=len(history),
        kept_count=len(kept),
        original_chars=original_chars,
        kept_chars=kept_chars,
        estimated_tokens_before=_estimate_tokens(protected_chars + original_chars, chars_per_token),
        estimated_tokens_after=_estimate_tokens(
            protected_chars + kept_chars + summary_chars,
            chars_per_token,
        ),
        tool_payloads_trimmed=trimmed_count,
        reason=",".join(reasons) or "within_budget",
    )


def merge_history_summaries(existing: str, current: str, max_chars: int) -> str:
    existing = existing.strip()
    current = current.strip()
    if not existing:
        return current[:max_chars]
    if not current:
        return existing[:max_chars]
    combined = f"Earlier context:\n{existing}\nNewly compacted context:\n{current}"
    if len(combined) <= max_chars:
        return combined
    older_budget = max(0, max_chars // 2 - len("Earlier context:\n"))
    older = existing[:older_budget]
    prefix = f"Earlier context:\n{older}\nNewly compacted context:\n"
    return prefix + current[: max(0, max_chars - len(prefix))]


def _message_chars(item: AgentHistoryMessage) -> int:
    structured = {
        "tool_calls": item.tool_calls,
        "sources": item.sources,
        "citations": item.citations,
    }
    return len(item.content) + len(json.dumps(structured, ensure_ascii=False, default=str))


def _soft_trim_tool_payloads(
    messages: list[AgentHistoryMessage],
    limit: int,
    max_history_chars: int,
) -> int:
    if limit < 0:
        return 0
    trimmed = 0
    for message in messages:
        for source in message.sources:
            if sum(_message_chars(item) for item in messages) <= max_history_chars:
                return trimmed
            text = str(source.get("text") or "")
            if len(text) > limit:
                source["text"] = f"{text[:limit]}…[trimmed]"
                source["text_trimmed"] = True
                trimmed += 1
        for citation in message.citations:
            if sum(_message_chars(item) for item in messages) <= max_history_chars:
                return trimmed
            quote = str(citation.get("quote") or "")
            if len(quote) > limit:
                citation["quote"] = f"{quote[:limit]}…[trimmed]"
                citation["quote_trimmed"] = True
                trimmed += 1
    return trimmed


def _hard_clear_tool_payloads(
    messages: list[AgentHistoryMessage],
    max_history_chars: int,
) -> int:
    cleared = 0
    for message in messages:
        for source in message.sources:
            if sum(_message_chars(item) for item in messages) <= max_history_chars:
                return cleared
            if source.get("text"):
                source["text"] = ""
                source["text_trimmed"] = True
                cleared += 1
        for citation in message.citations:
            if sum(_message_chars(item) for item in messages) <= max_history_chars:
                return cleared
            if citation.get("quote"):
                citation["quote"] = ""
                citation["quote_trimmed"] = True
                cleared += 1
    return cleared


def _estimate_tokens(char_count: int, chars_per_token: float) -> int:
    return math.ceil(char_count / max(chars_per_token, 0.1))


def _summarize_removed_messages(messages: list[AgentHistoryMessage], max_chars: int) -> str:
    if not messages or max_chars <= 0:
        return ""
    lines: list[str] = []
    for item in messages:
        content = " ".join(item.content.split())
        label = "user_request_or_constraint" if item.role == "user" else "assistant_decision"
        _append_summary_line(lines, f"{label}: {_summary_text(content)}", max_chars)
        for call in item.tool_calls:
            source_ids = ",".join(str(value) for value in (call.get("source_ids") or [])) or "none"
            detail = (
                f"tool:{call.get('name') or 'unknown'} outcome={call.get('outcome') or 'unknown'} "
                f"error={call.get('error_kind') or 'none'} sources={source_ids}"
            )
            error_message = str(call.get("error_message") or "").strip()
            if error_message:
                detail += f" reason={error_message[:160]}"
            _append_summary_line(lines, detail, max_chars)
        citation_ids = [
            str(citation.get("source_id") or "")
            for citation in item.citations
            if citation.get("source_id")
        ]
        if citation_ids:
            _append_summary_line(lines, f"citations:{','.join(citation_ids)}", max_chars)
        if len("\n".join(lines)) >= max_chars:
            break
    return "\n".join(lines)[:max_chars]


def _append_summary_line(lines: list[str], line: str, max_chars: int) -> None:
    separator_chars = 1 if lines else 0
    remaining = max_chars - len("\n".join(lines)) - separator_chars
    if remaining > 0:
        lines.append(line[:remaining])


def _summary_text(content: str, limit: int = 400) -> str:
    if len(content) <= limit:
        return content
    tail_chars = min(150, limit // 2)
    head_chars = max(0, limit - tail_chars - len(" … "))
    return f"{content[:head_chars]} … {content[-tail_chars:]}"
