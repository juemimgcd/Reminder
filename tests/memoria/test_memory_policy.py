import pytest

from app.mneme.memoria.server.memory.policy import AUTO_PROMOTION_CONFIDENCE, classify_candidate
from app.mneme.memoria.server.memory.sensitivity import classify_sensitivity, contains_secret


@pytest.mark.parametrize(
    ("sensitivity", "confidence", "explicit", "conflict", "expected"),
    [
        ("low", AUTO_PROMOTION_CONFIDENCE, False, False, "promote"),
        ("low", AUTO_PROMOTION_CONFIDENCE - 0.01, False, False, "pending"),
        ("sensitive", 0.99, False, False, "pending"),
        ("secret", 0.99, True, False, "reject"),
        ("low", 0.99, False, True, "pending"),
        ("low", 0.2, True, True, "promote"),
    ],
)
def test_memory_policy_is_deterministic_at_confidence_and_governance_boundaries(
    sensitivity, confidence, explicit, conflict, expected
):
    assert classify_candidate(
        sensitivity=sensitivity,
        confidence=confidence,
        explicit_request=explicit,
        has_conflict=conflict,
    ) == expected


def test_sensitive_and_secret_values_are_classified_before_persistence():
    assert contains_secret("api_key = sk-abcdefghijklmnopqrstuvwxyz")
    assert classify_sensitivity("my diagnosis is private") == "sensitive"
    assert classify_sensitivity("password = super-secret-value") == "secret"
    assert classify_sensitivity("I prefer markdown") == "low"


def test_policy_rejects_invalid_confidence_without_silently_promoting():
    with pytest.raises(ValueError, match="between 0 and 1"):
        classify_candidate(sensitivity="low", confidence=1.1)
