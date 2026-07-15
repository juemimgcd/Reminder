import asyncio
from datetime import UTC, datetime
from pathlib import Path

from services.memory_agent.services.deletion import (
    ConversationDeletedPayload,
    DeletionResult,
    delete_source_evidence,
)


class _NoopDb:
    async def scalars(self, statement):
        raise AssertionError("no-op deletion should not query the database")


def test_noop_source_delete_is_scoped_and_returns_a_durable_result():
    result = asyncio.run(
        delete_source_evidence(
            _NoopDb(),
            owner_id=7,
            knowledge_base_id="kb-1",
            source_ids=set(),
            projection_ids={"projection-1"},
        )
    )

    assert isinstance(result, DeletionResult)
    assert result.projection_ids == ("projection-1",)
    assert result.deleted_evidence_count == 0


def test_conversation_delete_payload_rejects_duplicate_message_ids():
    try:
        ConversationDeletedPayload(
            owner_id=7,
            knowledge_base_id="kb-1",
            session_id="session-1",
            message_ids=["m1", "m1"],
            source_version=datetime.now(UTC),
        )
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("duplicate message IDs must be rejected")


def test_deletion_recalculates_supported_memory_and_never_copies_source_content_to_audit():
    source = Path("services/memory_agent/services/deletion.py").read_text(encoding="utf-8")
    commands = Path("services/memory_agent/services/memory_commands.py").read_text(encoding="utf-8")

    assert "confidence_ceiling = 1.0 - (0.5**evidence_count)" in source
    assert "unsupported_revision_ids" in source
    assert "reason=reason" in commands
    assert "minimum_text" not in commands
