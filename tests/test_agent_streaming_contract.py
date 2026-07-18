from app.mneme.domains.chat.service import _memory_agent_progress_to_event
from app.mneme.memoria.events import AgentEvent, AgentRunEventType
from app.mneme.memoria.persistence.runtime_events import parse_event_sequence
from app.mneme.memoria.schemas.memory_agent import MemoryAgentStreamEvent
from app.mneme.memoria.server.runtime.streaming import answer_chunks, phase_event_name


def test_agent_events_gain_stable_delivery_identity():
    event = AgentEvent.assistant_delta("validated answer")

    delivered = event.with_delivery(run_id="run-1", sequence=7)

    assert delivered.name == AgentRunEventType.ANSWER_DELTA
    assert delivered.schema_version == "2"
    assert delivered.run_id == "run-1"
    assert delivered.sequence == 7
    assert delivered.to_stream_dict()["content"] == "validated answer"


def test_event_cursor_accepts_stable_and_legacy_major_ids():
    assert parse_event_sequence(None) == 0
    assert parse_event_sequence("12") == 12
    assert parse_event_sequence("12-0") == 12


def test_validated_answer_chunks_reassemble_without_content_loss():
    answer = "Memory evidence and document evidence are both represented here."

    chunks = answer_chunks(answer, size=13)

    assert len(chunks) > 1
    assert "".join(chunks) == answer


def test_runtime_phases_map_to_public_rag_events_only():
    assert phase_event_name("retrieve", "started") == "retrieval.started"
    assert phase_event_name("generate", "started") == "answer.started"
    assert phase_event_name("citations", "completed") == "citation.resolved"
    assert phase_event_name("validate", "completed") is None
    assert phase_event_name("retrieve", "completed") is None
    assert phase_event_name("complete", "completed") is None


def test_memory_agent_delta_maps_to_frontend_answer_delta():
    progress = MemoryAgentStreamEvent(
        type="delta",
        sequence=4,
        name="answer.delta",
        run_id="memory-run-1",
        content="answer part",
    )

    event = _memory_agent_progress_to_event(
        progress,
        agent_run_id="run-1",
        trace_id="trace-1",
    )

    assert event is not None
    assert event.name == AgentRunEventType.ANSWER_DELTA
    assert event.content == "answer part"
    assert event.metadata == {
        "memory_agent_run_id": "memory-run-1",
        "trace_id": "trace-1",
    }


def test_public_retrieval_metadata_survives_bridge_without_private_inputs():
    progress = MemoryAgentStreamEvent(
        type="phase",
        sequence=3,
        name="retrieval.source_completed",
        run_id="memory-run-1",
        phase="retrieve",
        status="completed",
        public_payload={
            "evidence_count": 5,
            "source_counts": {"memory": 2, "document": 3},
        },
    )

    event = _memory_agent_progress_to_event(
        progress,
        agent_run_id="run-1",
        trace_id="trace-1",
    )

    assert event is not None
    assert event.name == AgentRunEventType.RETRIEVAL_SOURCE_COMPLETED
    assert event.metadata["evidence_count"] == 5
    assert event.metadata["source_counts"] == {"memory": 2, "document": 3}
    assert "question" not in event.metadata
    assert "model" not in event.metadata


def test_multi_agent_role_progress_survives_bridge_without_private_payloads():
    progress = MemoryAgentStreamEvent(
        type="phase",
        sequence=5,
        name="multi_agent.role.completed",
        run_id="memory-run-1",
        phase="multi_agent.retrieve",
        status="completed",
        public_payload={
            "agent_role": "memory_retriever",
            "source_type": "memory",
            "result_count": 3,
            "elapsed_ms": 14,
        },
    )

    event = _memory_agent_progress_to_event(
        progress,
        agent_run_id="run-1",
        trace_id="trace-1",
    )

    assert event is not None
    assert event.name == AgentRunEventType.MULTI_AGENT_ROLE_COMPLETED
    assert event.agent_role == "memory_retriever"
    assert event.metadata["result_count"] == 3
    assert "question" not in event.metadata
    assert "evidence" not in event.metadata
