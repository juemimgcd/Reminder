import math
from dataclasses import dataclass

from app.mneme.agent.contracts import AgentHistoryMessage


@dataclass(frozen=True)
class HistoryBudgetResult:
    messages: list[AgentHistoryMessage]
    summary: str
    original_count: int
    kept_count: int
    original_chars: int
    kept_chars: int
    estimated_tokens_before: int
    estimated_tokens_after: int
    reason: str

    @property
    def was_compacted(self) -> bool:
        return self.kept_count < self.original_count


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
) -> HistoryBudgetResult:
    original_chars = sum(len(item.content) for item in history)
    protected_chars = system_chars + current_question_chars
    available_tokens = max(
        0,
        context_window_tokens - output_reserve_tokens - _estimate_tokens(protected_chars, chars_per_token),
    )
    max_history_chars = int(available_tokens * chars_per_token)
    max_messages = max(2, max_turns * 2)
    kept = list(history[-max_messages:])
    reasons: list[str] = []
    if len(kept) < len(history):
        reasons.append("turn_limit")

    # The most recent user/assistant follow-up pair stays intact even if it alone
    # exceeds the configured history budget.
    while len(kept) > 2 and sum(len(item.content) for item in kept) > max_history_chars:
        kept.pop(0)
        if "context_window_budget" not in reasons:
            reasons.append("context_window_budget")

    removed_count = len(history) - len(kept)
    removed = history[:removed_count]
    summary = _summarize_removed_messages(removed, summary_max_chars)
    kept_chars = sum(len(item.content) for item in kept)
    summary_chars = len(summary)
    return HistoryBudgetResult(
        messages=kept,
        summary=summary,
        original_count=len(history),
        kept_count=len(kept),
        original_chars=original_chars,
        kept_chars=kept_chars,
        estimated_tokens_before=_estimate_tokens(protected_chars + original_chars, chars_per_token),
        estimated_tokens_after=_estimate_tokens(protected_chars + kept_chars + summary_chars, chars_per_token),
        reason=",".join(reasons) or "within_budget",
    )


def _estimate_tokens(char_count: int, chars_per_token: float) -> int:
    return math.ceil(char_count / max(chars_per_token, 0.1))


def _summarize_removed_messages(messages: list[AgentHistoryMessage], max_chars: int) -> str:
    if not messages or max_chars <= 0:
        return ""
    lines: list[str] = []
    for item in messages:
        content = " ".join(item.content.split())
        line = f"{item.role}: {content[:400]}"
        separator_chars = 1 if lines else 0
        remaining = max_chars - len("\n".join(lines)) - separator_chars
        if remaining <= 0:
            break
        lines.append(line[:remaining])
    return "\n".join(lines)
