from pathlib import Path

CHAT_SERVICE = Path(__file__).parents[1] / "app" / "mneme" / "domains" / "chat" / "service.py"


def test_cutover_flag_has_exclusive_legacy_and_agent_branches():
    source = CHAT_SERVICE.read_text(encoding="utf-8")

    assert "if not settings.MEMORY_AGENT_ENABLED:" in source
    assert "build_mneme_agent(db).run(" in source
    assert "answer_via_memory_agent(" in source
    flag_index = source.index("if not settings.MEMORY_AGENT_ENABLED:")
    agent_branch = source[flag_index : source.index("    model_config = await _resolve_model_config", flag_index)]
    assert "answer_via_memory_agent" not in agent_branch


def test_agent_failure_is_mapped_to_retryable_saved_message_without_legacy_fallback():
    source = CHAT_SERVICE.read_text(encoding="utf-8")
    failure_start = source.index("except MemoryAgentUnavailable")
    failure_end = source.index("    result = memory_agent_answer_to_chat_result", failure_start)
    failure_block = source[failure_start:failure_end]
    assert '"retryable": True' in failure_block
    assert "build_mneme_agent" not in failure_block
