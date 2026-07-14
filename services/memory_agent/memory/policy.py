from typing import Literal

from services.memory_agent.models.memory_candidate import Sensitivity

AUTO_PROMOTION_CONFIDENCE = 0.85
PolicyDecision = Literal["promote", "pending", "reject"]


def classify_candidate(
    *,
    sensitivity: Sensitivity,
    confidence: float,
    explicit_request: bool = False,
    has_conflict: bool = False,
) -> PolicyDecision:
    if sensitivity not in {"low", "sensitive", "secret"}:
        raise ValueError("unsupported sensitivity")
    if sensitivity == "secret":
        return "reject"
    if explicit_request:
        return "promote"
    if has_conflict or sensitivity == "sensitive" or confidence < AUTO_PROMOTION_CONFIDENCE:
        return "pending"
    return "promote"
