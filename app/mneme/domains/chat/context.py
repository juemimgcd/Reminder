import json
import math
from collections.abc import Sequence
from dataclasses import dataclass

from app.mneme.memoria.context_governance import (
    ContextAssemblyReport,
    ContextSource,
    ContextSourceDecision,
    assemble_critical_context,
    sanitize_context_text,
)
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
    assembly_report: ContextAssemblyReport


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
    critical_items: Sequence[ContextSource] | None = None,
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
    token_budget = max(256, max_context_tokens or 256)
    baseline = _prepare_history_context(
        unsummarized,
        existing_summary=existing_summary,
        summary_through_message_id=summary_through_message_id,
        max_messages=max_messages,
        summary_max_chars=summary_max_chars,
        token_budget=token_budget,
        chars_per_token=safe_chars_per_token,
        tool_result_soft_chars=tool_result_soft_chars,
    )
    try:
        structured_critical_items = [
            *(critical_items or ()),
            *_extract_structured_critical_items(eligible),
        ]
        critical = assemble_critical_context(
            structured_critical_items,
            token_budget=token_budget,
            chars_per_token=safe_chars_per_token,
        )
    except Exception:
        return _with_assembly_report(
            baseline,
            _history_assembly_report(
                eligible,
                unsummarized=unsummarized,
                existing_summary=existing_summary,
                prepared=baseline,
                token_budget=token_budget,
                chars_per_token=safe_chars_per_token,
            ),
        )

    history_token_budget = max(0, token_budget - critical.report.estimated_tokens_after)
    history_summary_chars = max(0, 20_000 - len(critical.text) - (1 if critical.text else 0))
    prepared = _prepare_history_context(
        unsummarized,
        existing_summary=existing_summary,
        summary_through_message_id=summary_through_message_id,
        max_messages=max_messages,
        summary_max_chars=min(summary_max_chars, history_summary_chars),
        token_budget=history_token_budget,
        chars_per_token=safe_chars_per_token,
        tool_result_soft_chars=tool_result_soft_chars,
    )
    context_summary = "\n".join(
        part for part in (critical.text, prepared.context.summary) if part
    )
    context = prepared.context.model_copy(update={"summary": context_summary})
    history_report = _history_assembly_report(
        eligible,
        unsummarized=unsummarized,
        existing_summary=existing_summary,
        prepared=prepared,
        token_budget=token_budget,
        chars_per_token=safe_chars_per_token,
    )
    report = ContextAssemblyReport(
        token_budget=token_budget,
        estimated_tokens_before=(
            critical.report.estimated_tokens_before + baseline.before_tokens
        ),
        estimated_tokens_after=_estimate_text_tokens(
            context.summary,
            safe_chars_per_token,
        )
        + sum(
            _estimate_text_tokens(message.content, safe_chars_per_token)
            for message in context.messages
        ),
        decisions=[*critical.report.decisions, *history_report.decisions],
    )
    return PreparedConversationContext(
        context=context,
        persisted_summary=prepared.persisted_summary,
        persisted_summary_through_message_id=(
            prepared.persisted_summary_through_message_id
        ),
        before_tokens=report.estimated_tokens_before,
        after_tokens=report.estimated_tokens_after,
        compacted_messages=prepared.compacted_messages,
        compaction_reason=prepared.compaction_reason,
        assembly_report=report,
    )


def _prepare_history_context(
    unsummarized: Sequence[ChatMessage],
    *,
    existing_summary: str,
    summary_through_message_id: str | None,
    max_messages: int,
    summary_max_chars: int,
    token_budget: int,
    chars_per_token: float,
    tool_result_soft_chars: int,
) -> PreparedConversationContext:
    before_tokens = _estimate_text_tokens(
        existing_summary, chars_per_token
    ) + sum(
        _message_token_estimate(
            message,
            chars_per_token=chars_per_token,
            tool_result_soft_chars=tool_result_soft_chars,
        )
        for message in unsummarized
    )
    recent_count = max(0, min(max_messages, 24))
    compacted = list(unsummarized[:-recent_count] if recent_count else unsummarized)
    recent = list(unsummarized[-recent_count:] if recent_count else [])
    compacted_for_turn_limit = len(compacted)

    effective_summary_max_chars = min(
        max(0, min(summary_max_chars, 20_000)),
        max(0, int(token_budget * chars_per_token / 3)),
    )
    bounded_existing_summary = _bounded_summary(
        existing_summary,
        [],
        max_chars=effective_summary_max_chars,
    )
    while recent and (
        _estimate_text_tokens(bounded_existing_summary, chars_per_token)
        + sum(
            _message_token_estimate(
                message,
                chars_per_token=chars_per_token,
                tool_result_soft_chars=tool_result_soft_chars,
            )
            for message in recent
        )
        > token_budget
    ):
        compacted.append(recent.pop(0))

    summary_entries = [_summary_entry(message) for message in compacted]
    persisted_summary = _bounded_summary(
        bounded_existing_summary,
        summary_entries,
        max_chars=effective_summary_max_chars,
    )
    while recent and (
        _estimate_text_tokens(persisted_summary, chars_per_token)
        + sum(
            _estimate_text_tokens(message.content, chars_per_token)
            for message in recent
        )
        > token_budget
    ):
        compacted.append(recent.pop(0))
        persisted_summary = _bounded_summary(
            bounded_existing_summary,
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
        chars_per_token,
    ) + sum(
        _estimate_text_tokens(message.content, chars_per_token)
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
        assembly_report=ContextAssemblyReport(
            token_budget=token_budget,
            estimated_tokens_before=before_tokens,
            estimated_tokens_after=after_tokens,
        ),
    )


def _extract_structured_critical_items(messages: Sequence[ChatMessage]) -> list[ContextSource]:
    items: list[ContextSource] = []
    seen: set[tuple[str, str]] = set()
    for message in messages:
        for payload in (*(message.sources_json or []), *(message.citations_json or [])):
            if not isinstance(payload, dict):
                continue
            identifier = next(
                (
                    payload.get(key)
                    for key in ("evidence_id", "source_id", "document_id", "chunk_id")
                    if isinstance(payload.get(key), str) and payload.get(key)
                ),
                None,
            )
            if identifier is None or ("citation", identifier) in seen:
                continue
            seen.add(("citation", identifier))
            items.append(
                ContextSource(
                    source_id=f"citation:{identifier}"[:256],
                    source_type="citation",
                    content=f"Cited evidence identifier: {identifier}",
                )
            )
        for index, payload in enumerate(message.tool_calls_json or []):
            if not isinstance(payload, dict):
                continue
            status = payload.get("status")
            if status in {"approval_required", "pending"}:
                identifier = _safe_identifier(
                    payload.get("approval_id") or payload.get("tool_call_id"),
                    fallback=f"{message.id}:{index}",
                )
                if ("approval", identifier) in seen:
                    continue
                seen.add(("approval", identifier))
                action = _safe_label(payload.get("name"), fallback="write action")
                summary = _safe_label(payload.get("summary"), fallback="awaiting user decision")
                items.append(
                    ContextSource(
                        source_id=identifier,
                        source_type="approval",
                        content=f"Unresolved approval {identifier}: {action} - {summary}",
                    )
                )
            elif status == "failed":
                identifier = _safe_identifier(
                    payload.get("tool_call_id"),
                    fallback=f"{message.id}:{index}",
                )
                if ("tool_failure", identifier) in seen:
                    continue
                seen.add(("tool_failure", identifier))
                tool = _safe_label(payload.get("name"), fallback="tool")
                code = _safe_label(payload.get("code"), fallback="unknown failure")
                items.append(
                    ContextSource(
                        source_id=identifier,
                        source_type="tool_failure",
                        content=f"{tool} failed ({code})",
                    )
                )
    return items


def _safe_identifier(value: object, *, fallback: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback[:256]
    return sanitize_context_text(value)[:256]


def _safe_label(value: object, *, fallback: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    return sanitize_context_text(value)[:256]


def _history_assembly_report(
    eligible: Sequence[ChatMessage],
    *,
    unsummarized: Sequence[ChatMessage],
    existing_summary: str,
    prepared: PreparedConversationContext,
    token_budget: int,
    chars_per_token: float,
) -> ContextAssemblyReport:
    decisions: list[ContextSourceDecision] = []
    if existing_summary:
        persisted = prepared.persisted_summary
        if not persisted:
            outcome = "dropped"
        elif existing_summary.strip() in persisted:
            outcome = "included"
        else:
            outcome = "truncated"
        decisions.append(
            ContextSourceDecision(
                source_id="history-summary",
                source_type="history_summary",
                outcome=outcome,
                input_chars=len(existing_summary),
                output_chars=min(len(existing_summary), len(persisted)),
                reason="reused existing bounded history summary",
            )
        )

    unsummarized_ids = {message.id for message in unsummarized}
    included_by_id = {message.message_id: message for message in prepared.context.messages}
    for message in eligible:
        included = included_by_id.get(message.id)
        if included is not None:
            outcome = "included"
            output_chars = len(included.content)
            reason = "included as recent conversation"
        elif message.id not in unsummarized_ids:
            outcome = "dropped"
            output_chars = 0
            reason = "already covered by the prior summary watermark"
        elif prepared.persisted_summary:
            outcome = "truncated"
            output_chars = min(len(_summary_entry(message)), len(prepared.persisted_summary))
            reason = "compacted into the bounded history summary"
        else:
            outcome = "dropped"
            output_chars = 0
            reason = "history budget exhausted"
        decisions.append(
            ContextSourceDecision(
                source_id=message.id,
                source_type="history_message",
                outcome=outcome,
                input_chars=len(message.content),
                output_chars=output_chars,
                reason=reason,
            )
        )
    return ContextAssemblyReport(
        token_budget=token_budget,
        estimated_tokens_before=prepared.before_tokens,
        estimated_tokens_after=prepared.after_tokens,
        decisions=decisions,
    )


def _with_assembly_report(
    prepared: PreparedConversationContext,
    report: ContextAssemblyReport,
) -> PreparedConversationContext:
    return PreparedConversationContext(
        context=prepared.context,
        persisted_summary=prepared.persisted_summary,
        persisted_summary_through_message_id=prepared.persisted_summary_through_message_id,
        before_tokens=prepared.before_tokens,
        after_tokens=prepared.after_tokens,
        compacted_messages=prepared.compacted_messages,
        compaction_reason=prepared.compaction_reason,
        assembly_report=report,
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
