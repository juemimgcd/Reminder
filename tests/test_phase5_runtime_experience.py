import os
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

os.environ.setdefault("MEMORY_AGENT_SERVICE_JWT_SECRET", "test-only-phase5-secret")

from app.mneme.domains.chat.context import prepare_conversation_context
from app.mneme.memoria.api.runs import _build_controlled_run
from app.mneme.memoria.run_models import AgentRunRecord
from app.mneme.memoria.server.providers.llm import (
    _Failure,
    _ProviderHealthRegistry,
    _ResolvedConfig,
)
from app.mneme.models.chat_message import ChatMessage
from app.mneme.schemas.chat_session import AgentRunControlRequest


def _run() -> AgentRunRecord:
    return AgentRunRecord.create(
        run_id="run-original",
        session_id="session-1",
        user_id=7,
        client_request_id="request-original",
        question="original question",
        top_k=6,
        answer_mode="analysis_query",
        execution_mode="multi",
    )


def _message(message_id: str, role: str, content: str) -> ChatMessage:
    return ChatMessage(
        id=message_id,
        session_id="session-1",
        user_id=7,
        knowledge_base_id=None,
        knowledge_base_pk=None,
        role=role,
        content=content,
        sources_json=[],
        tool_calls_json=[],
        created_at=datetime.now(timezone.utc),
    )


def test_steer_requires_an_updated_instruction():
    with pytest.raises(ValidationError):
        AgentRunControlRequest(mode="steer")


def test_controlled_run_inherits_runtime_choices_and_links_to_target():
    controlled = _build_controlled_run(
        _run(),
        AgentRunControlRequest(mode="followup", question="next question"),
        default_execution_mode="single",
        user_id=7,
    )

    assert controlled.trigger_type == "followup"
    assert controlled.trigger_id == "run-original"
    assert controlled.top_k == 6
    assert controlled.answer_mode == "analysis_query"
    assert controlled.execution_mode == "multi"


def test_context_compaction_obeys_token_budget_and_reports_reason():
    messages = [
        _message("message-1", "user", "a" * 200),
        _message("message-2", "assistant", "b" * 200),
        _message("message-current", "user", "current"),
    ]

    prepared = prepare_conversation_context(
        messages,
        current_message_id="message-current",
        existing_summary="",
        summary_through_message_id=None,
        max_messages=10,
        summary_max_chars=30,
        max_context_tokens=256,
        chars_per_token=1,
    )

    assert prepared.before_tokens == 400
    assert prepared.after_tokens <= 256
    assert prepared.compacted_messages == 1
    assert prepared.compaction_reason == "context_window_pressure"
    assert prepared.persisted_summary_through_message_id == "message-1"


def test_unhealthy_provider_enters_cooldown_and_recovers_after_success():
    registry = _ProviderHealthRegistry(failure_threshold=2, cooldown_seconds=30)
    config = _ResolvedConfig(
        provider="test",
        base_url="https://model.invalid",
        model_name="test-model",
        temperature=0,
        context_window=4096,
        api_key="secret",
    )
    failure = _Failure("AGENT_MODEL_UNAVAILABLE", True)

    registry.record_failure(config, failure)
    assert registry.is_available(config)
    registry.record_failure(config, failure)
    assert not registry.is_available(config)
    registry.record_success(config)
    assert registry.is_available(config)
