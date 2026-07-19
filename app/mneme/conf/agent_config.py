from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

DEFAULT_BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_MEMORIA_CONFIG_PATH = DEFAULT_BASE_DIR / "memoria.json"
_ENV_REFERENCE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


class AgentConfigError(RuntimeError):
    """Raised when memoria.json cannot be loaded or validated."""


class _ConfigModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class AgentModelConfig(_ConfigModel):
    provider: str = "deepseek"
    model: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com"
    api_key: SecretStr = SecretStr("")
    temperature: float = Field(default=0.0, ge=0, le=2)
    context_window: int = Field(default=64000, ge=1000, le=1000000)


class ChatHistoryConfig(_ConfigModel):
    max_turns: int = Field(default=12, ge=1, le=100)
    output_reserve_tokens: int = Field(default=4096, ge=128, le=32000)
    summary_max_chars: int = Field(default=2000, ge=100, le=20000)
    chars_per_token: float = Field(default=3.0, ge=1, le=8)
    tool_result_soft_chars: int = Field(default=600, ge=100, le=20000)


class ChatRetrievalConfig(_ConfigModel):
    vector_recall_k: int = Field(default=12, ge=1, le=100)
    keyword_recall_k: int = Field(default=12, ge=1, le=100)
    memory_recall_k: int = Field(default=8, ge=1, le=100)
    rerank_candidate_k: int = Field(default=20, ge=1, le=200)
    context_budget_chars: int = Field(default=4000, ge=500, le=200000)


class ChatAgentConfig(_ConfigModel):
    model: AgentModelConfig = Field(default_factory=AgentModelConfig)
    history: ChatHistoryConfig = Field(default_factory=ChatHistoryConfig)
    retrieval: ChatRetrievalConfig = Field(default_factory=ChatRetrievalConfig)


class RetryConfig(_ConfigModel):
    max_attempts: int = Field(default=3, ge=1, le=5)
    base_seconds: float = Field(default=0.5, ge=0, le=30)
    max_seconds: float = Field(default=4.0, ge=0, le=60)


class AnswerLimitsConfig(_ConfigModel):
    max_context_chars: int = Field(default=24000, ge=1000, le=100000)
    context_chars_per_token: float = Field(default=3.0, ge=1, le=8)
    prompt_reserve_tokens: int = Field(default=1024, ge=256, le=16000)
    max_question_chars: int = Field(default=8000, ge=100, le=20000)
    max_output_tokens: int = Field(default=1200, ge=100, le=8000)


class ReasoningConfig(_ConfigModel):
    max_steps: int = Field(default=3, ge=1, le=5)
    summary_max_chars: int = Field(default=600, ge=100, le=2000)
    total_output_tokens: int = Field(default=3600, ge=100, le=16000)


class ToolConfig(_ConfigModel):
    max_calls: int = Field(default=4, ge=0, le=12)
    observation_max_chars: int = Field(default=2000, ge=200, le=8000)


class MultiAgentConfig(_ConfigModel):
    enabled: bool = True
    rollout_percent: int = Field(default=100, ge=0, le=100)
    allowed_modes: list[str] = Field(default_factory=lambda: ["analysis_query"])
    deadline_seconds: float = Field(default=20, gt=0, le=120)
    source_timeout_seconds: float = Field(default=8, gt=0, le=60)
    max_model_calls: int = Field(default=4, ge=1, le=16)
    max_prompt_tokens: int = Field(default=12000, ge=512, le=200000)
    max_completion_tokens: int = Field(default=3600, ge=128, le=32000)
    max_retrieval_top_k: int = Field(default=24, ge=1, le=40)
    max_estimated_cost: float = Field(default=1.0, ge=0, le=100)


class MemoryAgentConfig(_ConfigModel):
    extraction_model: AgentModelConfig = Field(default_factory=AgentModelConfig)
    answer_model: AgentModelConfig = Field(default_factory=AgentModelConfig)
    fallback_model: AgentModelConfig = Field(
        default_factory=lambda: AgentModelConfig(provider="openai", model=""),
    )
    retry: RetryConfig = Field(default_factory=RetryConfig)
    answer: AnswerLimitsConfig = Field(default_factory=AnswerLimitsConfig)
    reasoning: ReasoningConfig = Field(default_factory=ReasoningConfig)
    tools: ToolConfig = Field(default_factory=ToolConfig)
    multi_agent: MultiAgentConfig = Field(default_factory=MultiAgentConfig)


class MemoriaConfig(_ConfigModel):
    version: int = Field(default=1, ge=1)
    chat: ChatAgentConfig = Field(default_factory=ChatAgentConfig)
    memory_agent: MemoryAgentConfig = Field(default_factory=MemoryAgentConfig)


def _expand_env_references(value: Any) -> Any:
    if isinstance(value, str):
        match = _ENV_REFERENCE.fullmatch(value)
        return os.environ.get(match.group(1), "") if match else value
    if isinstance(value, list):
        return [_expand_env_references(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env_references(item) for key, item in value.items()}
    return value


def resolve_memoria_config_path(config_path: str | Path | None = None) -> Path:
    configured = config_path or os.environ.get("MEMORIA_CONFIG_PATH")
    path = Path(configured) if configured else DEFAULT_MEMORIA_CONFIG_PATH
    if not path.is_absolute():
        path = DEFAULT_BASE_DIR / path
    return path.resolve()


def load_memoria_config(config_path: str | Path | None = None) -> MemoriaConfig:
    load_dotenv(DEFAULT_BASE_DIR / ".env", override=False)
    path = resolve_memoria_config_path(config_path)
    try:
        raw_config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AgentConfigError(f"Memoria agent config not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentConfigError(f"Memoria agent config is unreadable: {path}") from exc
    try:
        return MemoriaConfig.model_validate(_expand_env_references(raw_config))
    except ValidationError as exc:
        raise AgentConfigError(f"Memoria agent config is invalid: {path}: {exc}") from exc


def mneme_agent_settings(config: MemoriaConfig) -> dict[str, Any]:
    model = config.chat.model
    history = config.chat.history
    retrieval = config.chat.retrieval
    return {
        "LLM_PROVIDER": model.provider,
        "LLM_API_KEY": model.api_key.get_secret_value(),
        "LLM_BASE_URL": model.base_url,
        "LLM_MODEL_NAME": model.model,
        "LLM_TEMPERATURE": model.temperature,
        "LLM_CONTEXT_WINDOW": model.context_window,
        "AGENT_HISTORY_MAX_TURNS": history.max_turns,
        "AGENT_OUTPUT_RESERVE_TOKENS": history.output_reserve_tokens,
        "AGENT_SUMMARY_MAX_CHARS": history.summary_max_chars,
        "AGENT_CHARS_PER_TOKEN": history.chars_per_token,
        "AGENT_TOOL_RESULT_SOFT_CHARS": history.tool_result_soft_chars,
        "RETRIEVAL_VECTOR_RECALL_K": retrieval.vector_recall_k,
        "RETRIEVAL_KEYWORD_RECALL_K": retrieval.keyword_recall_k,
        "RETRIEVAL_MEMORY_RECALL_K": retrieval.memory_recall_k,
        "RETRIEVAL_RERANK_CANDIDATE_K": retrieval.rerank_candidate_k,
        "RETRIEVAL_CONTEXT_BUDGET_CHARS": retrieval.context_budget_chars,
    }


def memory_agent_settings(config: MemoriaConfig) -> dict[str, Any]:
    agent = config.memory_agent
    extraction = agent.extraction_model
    answer = agent.answer_model
    fallback = agent.fallback_model
    return {
        "EXTRACTION_LLM_BASE_URL": extraction.base_url,
        "EXTRACTION_LLM_API_KEY": extraction.api_key,
        "EXTRACTION_LLM_MODEL": extraction.model,
        "EXTRACTION_LLM_TEMPERATURE": extraction.temperature,
        "ANSWER_LLM_PROVIDER": answer.provider,
        "ANSWER_LLM_BASE_URL": answer.base_url,
        "ANSWER_LLM_API_KEY": answer.api_key,
        "ANSWER_LLM_MODEL": answer.model,
        "ANSWER_LLM_TEMPERATURE": answer.temperature,
        "ANSWER_LLM_CONTEXT_WINDOW": answer.context_window,
        "ANSWER_LLM_MAX_ATTEMPTS": agent.retry.max_attempts,
        "ANSWER_LLM_RETRY_BASE_SECONDS": agent.retry.base_seconds,
        "ANSWER_LLM_RETRY_MAX_SECONDS": agent.retry.max_seconds,
        "ANSWER_LLM_FALLBACK_PROVIDER": fallback.provider,
        "ANSWER_LLM_FALLBACK_BASE_URL": fallback.base_url,
        "ANSWER_LLM_FALLBACK_API_KEY": fallback.api_key,
        "ANSWER_LLM_FALLBACK_MODEL": fallback.model,
        "ANSWER_LLM_FALLBACK_TEMPERATURE": fallback.temperature,
        "ANSWER_LLM_FALLBACK_CONTEXT_WINDOW": fallback.context_window,
        "ANSWER_MAX_CONTEXT_CHARS": agent.answer.max_context_chars,
        "ANSWER_CONTEXT_CHARS_PER_TOKEN": agent.answer.context_chars_per_token,
        "ANSWER_PROMPT_RESERVE_TOKENS": agent.answer.prompt_reserve_tokens,
        "ANSWER_MAX_QUESTION_CHARS": agent.answer.max_question_chars,
        "ANSWER_MAX_OUTPUT_TOKENS": agent.answer.max_output_tokens,
        "ANSWER_REASONING_MAX_STEPS": agent.reasoning.max_steps,
        "ANSWER_REASONING_SUMMARY_MAX_CHARS": agent.reasoning.summary_max_chars,
        "ANSWER_REASONING_TOTAL_OUTPUT_TOKENS": agent.reasoning.total_output_tokens,
        "ANSWER_TOOL_MAX_CALLS": agent.tools.max_calls,
        "ANSWER_TOOL_OBSERVATION_MAX_CHARS": agent.tools.observation_max_chars,
        "MULTI_AGENT_FEATURE_ENABLED": agent.multi_agent.enabled,
        "MULTI_AGENT_ROLLOUT_PERCENT": agent.multi_agent.rollout_percent,
        "MULTI_AGENT_ALLOWED_MODES": ",".join(agent.multi_agent.allowed_modes),
        "MULTI_AGENT_DEADLINE_SECONDS": agent.multi_agent.deadline_seconds,
        "MULTI_AGENT_SOURCE_TIMEOUT_SECONDS": agent.multi_agent.source_timeout_seconds,
        "MULTI_AGENT_MAX_MODEL_CALLS": agent.multi_agent.max_model_calls,
        "MULTI_AGENT_MAX_PROMPT_TOKENS": agent.multi_agent.max_prompt_tokens,
        "MULTI_AGENT_MAX_COMPLETION_TOKENS": agent.multi_agent.max_completion_tokens,
        "MULTI_AGENT_MAX_RETRIEVAL_TOP_K": agent.multi_agent.max_retrieval_top_k,
        "MULTI_AGENT_MAX_ESTIMATED_COST": agent.multi_agent.max_estimated_cost,
    }
