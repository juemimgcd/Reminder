from datetime import datetime, timezone

from app.mneme.domains.chat import context as chat_context
from app.mneme.domains.chat.context import prepare_conversation_context
from app.mneme.memoria.context_governance import ContextSource
from app.mneme.memoria.contracts import AgentRequest
from app.mneme.models.chat_message import ChatMessage


def _message(
    message_id: str,
    role: str,
    content: str,
    *,
    sources: list[dict] | None = None,
    citations: list[dict] | None = None,
    tool_calls: list[dict] | None = None,
) -> ChatMessage:
    return ChatMessage(
        id=message_id,
        session_id="session-1",
        user_id=7,
        knowledge_base_id=None,
        knowledge_base_pk=None,
        role=role,
        content=content,
        sources_json=sources or [],
        citations_json=citations or [],
        tool_calls_json=tool_calls or [],
        created_at=datetime.now(timezone.utc),
    )


def _prepare(
    messages: list[ChatMessage],
    *,
    critical_items: list[ContextSource] | None = None,
    max_messages: int = 10,
    summary_max_chars: int = 2_000,
    max_context_tokens: int = 512,
):
    return prepare_conversation_context(
        messages,
        current_message_id="message-current",
        existing_summary="",
        summary_through_message_id=None,
        max_messages=max_messages,
        summary_max_chars=summary_max_chars,
        max_context_tokens=max_context_tokens,
        chars_per_token=1,
        critical_items=critical_items,
    )


def test_user_directive_is_preserved_before_ordinary_history():
    prepared = _prepare(
        [
            _message("message-1", "assistant", "ordinary history"),
            _message("message-current", "user", "current"),
        ],
        critical_items=[
            ContextSource(
                source_id="directive-1",
                source_type="user_directive",
                content="Always answer in Chinese.",
            )
        ],
    )

    assert prepared.context.summary.startswith("[user_directive:directive-1] Always answer in Chinese.")
    assert prepared.context.messages[0].content == "ordinary history"
    assert prepared.assembly_report.decisions[0].source_id == "directive-1"
    assert prepared.assembly_report.decisions[0].outcome == "preserved"


def test_unresolved_approval_is_preserved_before_old_assistant_answer():
    prepared = _prepare(
        [
            _message(
                "message-1",
                "assistant",
                "old assistant answer",
                tool_calls=[
                    {
                        "name": "delete_memory",
                        "status": "approval_required",
                        "approval_id": "approval-1",
                        "summary": "Delete the duplicate memory",
                        "arguments": {"confirmation_token": "do-not-copy"},
                    }
                ],
            ),
            _message("message-current", "user", "current"),
        ],
        max_messages=0,
    )

    summary = prepared.context.summary
    assert summary.index("approval-1") < summary.index("old assistant answer")
    assert "do-not-copy" not in summary


def test_citation_identifier_survives_compaction_without_raw_tool_payload():
    prepared = _prepare(
        [
            _message(
                "message-1",
                "assistant",
                "old answer",
                sources=[{"source_id": "source-keep", "text": "x" * 5_000}],
                tool_calls=[
                    {
                        "name": "lookup",
                        "status": "completed",
                        "arguments": {"payload": "raw-payload-" * 500},
                    }
                ],
            ),
            _message("message-current", "user", "current"),
        ],
        max_messages=0,
        summary_max_chars=400,
    )

    assert "source-keep" in prepared.context.summary
    assert "raw-payload" not in prepared.context.summary


def test_failed_tool_is_short_and_secret_free():
    prepared = _prepare(
        [
            _message(
                "message-1",
                "assistant",
                "lookup failed",
                tool_calls=[
                    {
                        "tool_call_id": "call-1",
                        "name": "private_lookup",
                        "status": "failed",
                        "code": "UPSTREAM_TIMEOUT",
                        "error": "Bearer abc.def.ghi api_key=sk-super-secret-value",
                        "arguments": {"confirmation_token": "another-secret"},
                    }
                ],
            ),
            _message("message-current", "user", "current"),
        ],
        max_messages=0,
    )

    summary = prepared.context.summary
    assert "private_lookup failed (UPSTREAM_TIMEOUT)" in summary
    assert "abc.def.ghi" not in summary
    assert "sk-super-secret-value" not in summary
    assert "another-secret" not in summary
    failure = next(
        decision for decision in prepared.assembly_report.decisions if decision.source_type == "tool_failure"
    )
    assert failure.output_chars <= 512


def test_report_accounts_for_each_input_source():
    prepared = prepare_conversation_context(
        [
            _message("message-1", "user", "first"),
            _message("message-2", "assistant", "second"),
            _message("message-current", "user", "current"),
        ],
        current_message_id="message-current",
        existing_summary="older summary",
        summary_through_message_id=None,
        max_messages=1,
        summary_max_chars=2_000,
        max_context_tokens=512,
        chars_per_token=1,
        critical_items=[
            ContextSource(
                source_id="policy-1",
                source_type="system_policy",
                content="Do not reveal secrets.",
            )
        ],
    )

    decisions = {decision.source_id: decision for decision in prepared.assembly_report.decisions}
    assert set(decisions) == {"policy-1", "history-summary", "message-1", "message-2"}
    assert all(
        decision.outcome in {"included", "preserved", "truncated", "dropped"}
        for decision in decisions.values()
    )


def test_governance_failure_returns_original_safe_context(monkeypatch):
    messages = [
        _message("message-1", "assistant", "safe history"),
        _message("message-current", "user", "current"),
    ]
    baseline = _prepare(messages)

    def fail_governance(*args, **kwargs):
        raise RuntimeError("governance unavailable")

    monkeypatch.setattr(chat_context, "assemble_critical_context", fail_governance)
    fallback = _prepare(
        messages,
        critical_items=[
            ContextSource(
                source_id="directive-1",
                source_type="user_directive",
                content="Be concise.",
            )
        ],
    )

    assert fallback.context == baseline.context
    assert fallback.context.messages[0].content == "safe history"


def test_agent_request_stores_the_report_as_a_backward_compatible_dict():
    prepared = _prepare(
        [
            _message("message-1", "assistant", "safe history"),
            _message("message-current", "user", "current"),
        ]
    )

    request = AgentRequest(
        question="current",
        user_id=7,
        history_compaction=prepared.assembly_report,
    )

    assert isinstance(request.history_compaction, dict)
    assert request.history_compaction == prepared.assembly_report.model_dump(mode="json")


def test_recent_conversation_is_preserved_before_an_old_summary():
    prepared = prepare_conversation_context(
        [
            _message("message-1", "user", "recent instruction"),
            _message("message-current", "user", "current"),
        ],
        current_message_id="message-current",
        existing_summary="old summary " * 200,
        summary_through_message_id=None,
        max_messages=10,
        summary_max_chars=2_000,
        max_context_tokens=256,
        chars_per_token=1,
    )

    assert [message.content for message in prepared.context.messages] == ["recent instruction"]
    decision = next(
        item for item in prepared.assembly_report.decisions if item.source_id == "history-summary"
    )
    assert decision.outcome == "truncated"


def test_assembled_context_never_exceeds_the_reported_token_budget():
    prepared = _prepare(
        [_message("message-current", "user", "current")],
        critical_items=[
            ContextSource(
                source_id=f"directive-{index}",
                source_type="user_directive",
                content="x" * 100,
            )
            for index in range(10)
        ],
        max_context_tokens=256,
    )

    assert prepared.after_tokens <= prepared.assembly_report.token_budget


def test_source_identifiers_are_sanitized_in_context_and_report():
    prepared = _prepare(
        [_message("message-current", "user", "current")],
        critical_items=[
            ContextSource(
                source_id="sk-super-secret-value",
                source_type="citation",
                content="Cited evidence identifier: safe-source",
            )
        ],
    )

    assert "sk-super-secret-value" not in prepared.context.summary
    assert "sk-super-secret-value" not in prepared.assembly_report.model_dump_json()


def test_individually_bounded_items_are_reported_as_truncated():
    prepared = _prepare(
        [_message("message-current", "user", "current")],
        critical_items=[
            ContextSource(
                source_id="failure-1",
                source_type="tool_failure",
                content="x" * 500,
            )
        ],
    )

    decision = prepared.assembly_report.decisions[0]
    assert decision.outcome == "truncated"
    assert decision.output_chars <= 512
