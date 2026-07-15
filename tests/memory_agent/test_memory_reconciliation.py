from pathlib import Path

from services.memory_agent.memory.identity import memory_fingerprint, normalize_memory_text
from services.memory_agent.memory.reconciliation import _combined_confidence


def test_duplicate_reinforcement_combines_confidence_without_exceeding_one():
    assert _combined_confidence(0.8, 0.8) == 0.96
    assert _combined_confidence(1.0, 0.9) == 1.0


def test_memory_fingerprint_normalizes_whitespace_and_case():
    assert normalize_memory_text("  Alice   prefers  tea ") == "alice prefers tea"
    assert memory_fingerprint(subject="Alice", predicate="prefers", value="Tea") == memory_fingerprint(
        subject=" alice ", predicate="prefers", value="tea"
    )


def test_reconciliation_retains_revision_history_and_conflict_metadata():
    source = Path("services/memory_agent/memory/reconciliation.py").read_text(encoding="utf-8")

    assert "old_revision.valid_to = now" in source
    assert "conflicting_memory_id=conflict.memory_id" in source
    assert "reason=\"explicit_request_replacement\"" in source
    assert "candidate.status = \"promoted\"" in source
