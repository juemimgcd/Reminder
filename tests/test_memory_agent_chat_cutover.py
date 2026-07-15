from pathlib import Path

CHAT_SERVICE = Path(__file__).parents[1] / "app" / "mneme" / "domains" / "chat" / "service.py"
ONLINE_ROUTER_FILES = (
    CHAT_SERVICE,
    CHAT_SERVICE.parents[1] / "retrieval" / "router.py",
    CHAT_SERVICE.parents[1] / "companion" / "router.py",
)


def test_chat_answers_use_the_memory_agent_as_the_sole_runtime():
    for path in ONLINE_ROUTER_FILES:
        source = path.read_text(encoding="utf-8")
        assert "answer_via_memory_agent(" in source, path.name
        assert "build_mneme_agent" not in source, path.name
        assert "AgentRequest" not in source, path.name
        assert "MEMORY_AGENT_ENABLED" not in source, path.name

    source = CHAT_SERVICE.read_text(encoding="utf-8")
    assert "_persist_legacy_answer" not in source


def test_agent_failure_is_mapped_to_retryable_saved_message_without_legacy_fallback():
    source = CHAT_SERVICE.read_text(encoding="utf-8")
    failure_start = source.index("except MemoryAgentUnavailable")
    failure_end = source.index("    result = memory_agent_answer_to_chat_result", failure_start)
    failure_block = source[failure_start:failure_end]
    assert '"retryable": True' in failure_block
    assert "build_mneme_agent" not in failure_block
