from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.mneme.memoria.schemas.memory_agent import MemoryAgentEvent
from app.mneme.memoria.server.contracts.events import AgentEventEnvelope, DocumentProjectionPayload


def event_payload(**overrides):
    value = {
        "event_id": "evt-1",
        "event_type": "conversation.completed",
        "schema_version": "1",
        "occurred_at": datetime.now(UTC),
        "owner_id": 7,
        "knowledge_base_id": None,
        "payload": {"session_id": "session-1"},
    }
    value.update(overrides)
    return value


def test_event_envelope_accepts_the_version_one_contract():
    event = AgentEventEnvelope.model_validate(event_payload())

    assert event.schema_version == "1"
    assert event.owner_id == 7


@pytest.mark.parametrize(
    "override",
    [
        {"event_type": "unknown.event"},
        {"schema_version": "2"},
        {"occurred_at": datetime.now()},
        {"owner_id": 0},
    ],
)
def test_event_envelope_rejects_invalid_contract_values(override):
    with pytest.raises(ValidationError):
        AgentEventEnvelope.model_validate(event_payload(**override))


def test_event_envelope_rejects_unknown_fields():
    for contract in (AgentEventEnvelope, MemoryAgentEvent):
        with pytest.raises(ValidationError):
            contract.model_validate(event_payload(unexpected="not-versioned"))


def test_both_sides_reject_non_positive_owner_ids():
    for contract in (AgentEventEnvelope, MemoryAgentEvent):
        with pytest.raises(ValidationError):
            contract.model_validate(event_payload(owner_id=0))


def test_projection_payload_enforces_batch_bounds():
    with pytest.raises(ValidationError):
        DocumentProjectionPayload.model_validate(
            {
                "projection_id": "p1",
                "document_id": "d1",
                "document_version": "v1",
                "file_name": "doc.txt",
                "batch_index": 0,
                "batch_count": 0,
                "aggregate_hash": "a" * 64,
                "chunks": [],
            }
        )
