import json

import pytest

from app.mneme.conf.agent_config import (
    AgentConfigError,
    load_memoria_config,
    memory_agent_settings,
    mneme_agent_settings,
)
from app.mneme.conf.config import Settings
from app.mneme.memoria.server.config import MemoryAgentSettings


def _write_config(path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_memoria_json_expands_env_secrets_and_maps_agent_settings(tmp_path, monkeypatch):
    config_path = tmp_path / "memoria.json"
    monkeypatch.setenv("TEST_MEMORIA_API_KEY", "secret-from-env")
    _write_config(
        config_path,
        {
            "version": 1,
            "chat": {
                "model": {
                    "provider": "kimi",
                    "model": "kimi-custom",
                    "base_url": "https://llm.example/v1",
                    "api_key": "${TEST_MEMORIA_API_KEY}",
                    "temperature": 0.3,
                },
                "history": {"max_turns": 9},
                "retrieval": {"context_budget_chars": 9000},
            },
            "memory_agent": {
                "answer_model": {
                    "provider": "deepseek",
                    "model": "deepseek-answer",
                    "api_key": "${TEST_MEMORIA_API_KEY}",
                },
                "multi_agent": {
                    "enabled": False,
                    "allowed_modes": ["analysis_query", "memory_query"],
                },
            },
        },
    )

    config = load_memoria_config(config_path)
    mneme_values = mneme_agent_settings(config)
    memory_agent_values = memory_agent_settings(config)

    assert mneme_values["LLM_PROVIDER"] == "kimi"
    assert mneme_values["LLM_API_KEY"] == "secret-from-env"
    assert mneme_values["AGENT_HISTORY_MAX_TURNS"] == 9
    assert mneme_values["RETRIEVAL_CONTEXT_BUDGET_CHARS"] == 9000
    assert memory_agent_values["ANSWER_LLM_MODEL"] == "deepseek-answer"
    assert memory_agent_values["ANSWER_LLM_API_KEY"].get_secret_value() == "secret-from-env"
    assert memory_agent_values["MULTI_AGENT_FEATURE_ENABLED"] is False
    assert memory_agent_values["MULTI_AGENT_ALLOWED_MODES"] == "analysis_query,memory_query"


def test_memoria_json_values_override_legacy_agent_env_values(tmp_path):
    config_path = tmp_path / "memoria.json"
    env_path = tmp_path / ".env"
    _write_config(
        config_path,
        {
            "chat": {"model": {"provider": "deepseek"}},
            "memory_agent": {"multi_agent": {"rollout_percent": 25}},
        },
    )
    env_path.write_text(
        "LLM_PROVIDER=qwen\n"
        "MEMORY_AGENT_SERVICE_JWT_SECRET=test-secret\n"
        "MEMORY_AGENT_MULTI_AGENT_ROLLOUT_PERCENT=99\n",
        encoding="utf-8",
    )
    config = load_memoria_config(config_path)

    backend_settings = Settings(
        _env_file=env_path,
        **mneme_agent_settings(config),
    )
    memory_settings = MemoryAgentSettings(
        _env_file=env_path,
        **memory_agent_settings(config),
    )

    assert backend_settings.LLM_PROVIDER == "deepseek"
    assert memory_settings.MULTI_AGENT_ROLLOUT_PERCENT == 25


def test_memoria_json_rejects_invalid_agent_budgets(tmp_path):
    config_path = tmp_path / "memoria.json"
    _write_config(
        config_path,
        {
            "memory_agent": {
                "multi_agent": {
                    "rollout_percent": 101,
                },
            },
        },
    )

    with pytest.raises(AgentConfigError, match="Memoria agent config is invalid"):
        load_memoria_config(config_path)


def test_memoria_json_is_required(tmp_path):
    with pytest.raises(AgentConfigError, match="Memoria agent config not found"):
        load_memoria_config(tmp_path / "missing.json")
