import re

from services.memory_agent.memory.schemas import SensitivitySignal
from services.memory_agent.models.memory_candidate import Sensitivity

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(
        r"\b(?:password|passwd|pwd|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*[^\s,;]{6,}",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s:/]+:[^\s@]+@", re.IGNORECASE),
)

_SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:social security|ssn|passport|national id|身份证|护照)\b", re.IGNORECASE),
    re.compile(r"\b(?:diagnos(?:is|ed)|medical|medication|disease|病历|诊断|药物)\b", re.IGNORECASE),
    re.compile(r"\b(?:bank account|credit card|routing number|iban|银行卡|信用卡)\b", re.IGNORECASE),
    re.compile(r"\b(?:login|authentication|two-factor|2fa|登录|认证)\b", re.IGNORECASE),
)


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) is not None for pattern in _SECRET_PATTERNS)


def classify_sensitivity(
    *texts: str,
    model_signals: list[SensitivitySignal] | None = None,
) -> Sensitivity:
    if any(contains_secret(text) for text in texts):
        return "secret"
    if model_signals or any(
        pattern.search(text) is not None
        for text in texts
        for pattern in _SENSITIVE_PATTERNS
    ):
        return "sensitive"
    return "low"
