import math
import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ContextSourceType = Literal[
    "system_policy",
    "user_directive",
    "approval",
    "tool_failure",
    "citation",
    "history_summary",
    "history_message",
    "inferred_memory",
]
ContextSourceOutcome = Literal["included", "preserved", "truncated", "dropped"]


class ContextSource(BaseModel):
    source_id: str = Field(min_length=1, max_length=256)
    source_type: ContextSourceType
    content: str

    @field_validator("source_id")
    @classmethod
    def sanitize_source_id(cls, value: str) -> str:
        return sanitize_context_text(value)


class ContextSourceDecision(BaseModel):
    source_id: str
    source_type: ContextSourceType
    outcome: ContextSourceOutcome
    input_chars: int = Field(ge=0)
    output_chars: int = Field(ge=0)
    reason: str


class ContextAssemblyReport(BaseModel):
    schema_version: str = "1"
    token_budget: int = Field(ge=0)
    estimated_tokens_before: int = Field(ge=0)
    estimated_tokens_after: int = Field(ge=0)
    decisions: list[ContextSourceDecision] = Field(default_factory=list)


@dataclass(frozen=True)
class CriticalContextAssembly:
    text: str
    report: ContextAssemblyReport


_SOURCE_PRIORITY: dict[ContextSourceType, int] = {
    "system_policy": 0,
    "user_directive": 1,
    "approval": 2,
    "citation": 3,
    "tool_failure": 4,
    "inferred_memory": 5,
    "history_message": 6,
    "history_summary": 7,
}
_SOURCE_CHAR_LIMIT: dict[ContextSourceType, int] = {
    "system_policy": 2_000,
    "user_directive": 2_000,
    "approval": 800,
    "citation": 256,
    "tool_failure": 512,
    "inferred_memory": 1_000,
    "history_message": 2_000,
    "history_summary": 4_000,
}
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|confirmation[_-]?token|access[_-]?token|password|secret)\b"
    r"\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_API_TOKEN_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")


def assemble_critical_context(
    sources: list[ContextSource],
    *,
    token_budget: int,
    chars_per_token: float,
) -> CriticalContextAssembly:
    safe_chars_per_token = max(1.0, min(chars_per_token, 8.0))
    safe_token_budget = max(0, token_budget)
    remaining_chars = min(20_000, int(safe_token_budget * safe_chars_per_token))
    ordered = sorted(
        enumerate(sources),
        key=lambda item: (_SOURCE_PRIORITY[item[1].source_type], item[0]),
    )
    lines: list[str] = []
    decisions: list[ContextSourceDecision] = []

    for _, source in ordered:
        sanitized = sanitize_context_text(source.content)
        prefix = f"[{source.source_type}:{source.source_id}] "
        item_limit = _SOURCE_CHAR_LIMIT[source.source_type]
        bounded_content = sanitized[: max(0, item_limit - len(prefix))]
        candidate = prefix + bounded_content if bounded_content else ""
        separator_chars = 1 if lines else 0
        available_chars = max(0, remaining_chars - separator_chars)
        output = candidate[:available_chars] if available_chars > 0 else ""
        if not output or len(output) <= len(prefix):
            outcome: ContextSourceOutcome = "dropped"
            output = ""
            reason = "empty after sanitization" if not sanitized else "context budget exhausted"
        elif len(output) < len(candidate) or len(bounded_content) < len(sanitized):
            outcome = "truncated"
            reason = "bounded critical item to the configured context limit"
        else:
            outcome = "preserved"
            reason = "preserved by context precedence policy"

        if output:
            lines.append(output)
            remaining_chars -= len(output) + separator_chars
        decisions.append(
            ContextSourceDecision(
                source_id=source.source_id,
                source_type=source.source_type,
                outcome=outcome,
                input_chars=len(source.content),
                output_chars=len(output),
                reason=reason,
            )
        )

    text = "\n".join(lines)
    return CriticalContextAssembly(
        text=text,
        report=ContextAssemblyReport(
            token_budget=safe_token_budget,
            estimated_tokens_before=sum(
                _estimate_tokens(source.content, safe_chars_per_token) for source in sources
            ),
            estimated_tokens_after=_estimate_tokens(text, safe_chars_per_token),
            decisions=decisions,
        ),
    )


def sanitize_context_text(value: str) -> str:
    normalized = " ".join(value.split())
    normalized = _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", normalized)
    normalized = _BEARER_RE.sub("Bearer [REDACTED]", normalized)
    return _API_TOKEN_RE.sub("[REDACTED]", normalized)


def _estimate_tokens(value: str, chars_per_token: float) -> int:
    if not value:
        return 0
    return max(1, math.ceil(len(value) / chars_per_token))
