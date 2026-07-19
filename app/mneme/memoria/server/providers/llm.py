import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr, ValidationError, model_validator

from app.mneme.memoria.server.config import settings
from app.mneme.memoria.server.contracts.answers import ConversationContextData
from app.mneme.memoria.server.contracts.common import ModelInvocationConfig
from app.mneme.memoria.server.runtime.contracts import GeneratedAnswer, GenerationRequest
from app.mneme.memoria.server.runtime.orchestrator import RuntimeDependencyError
from app.mneme.memoria.server.runtime.prompts import build_messages
from app.mneme.memoria.server.runtime.reasoning import transition_reasoning_step
from app.mneme.memoria.server.runtime.tools import (
    ScopedToolExecutor,
    ToolRequest,
    available_tool_specs,
    bounded_observations,
    budget_exceeded_execution,
)


class _ProviderToolCall(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)


class _ProviderAnswer(BaseModel):
    decision: Literal["tool", "continue", "final"] = "final"
    reasoning_summary: str | None = Field(default=None, max_length=2000)
    answer: str = Field(min_length=1, max_length=20000)
    citations: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    confidence: float = Field(ge=0, le=1)
    uncertainty: str | None = Field(default=None, max_length=2000)
    insufficient_evidence: bool = False
    tool_calls: list[_ProviderToolCall] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_decision_payload(self) -> "_ProviderAnswer":
        if self.decision in {"continue", "tool"} and not (self.reasoning_summary or "").strip():
            raise ValueError("reasoning_summary is required when decision is not final")
        if (self.decision == "tool") != bool(self.tool_calls):
            raise ValueError("tool_calls must be non-empty only when decision is tool")
        return self


@dataclass(frozen=True)
class _ResolvedConfig:
    provider: str
    base_url: str
    model_name: str
    temperature: float
    context_window: int
    api_key: SecretStr
    fallback: bool = False


@dataclass(frozen=True)
class _Failure:
    code: str
    retryable: bool
    retry_after_seconds: float | None = None


@dataclass(frozen=True)
class _PromptBudget:
    question: str
    reasoning_chars: int
    conversation_chars: int
    evidence_chars: int
    output_tokens: int


@dataclass
class _ProviderHealthState:
    consecutive_failures: int = 0
    cooldown_until: float = 0.0


class _ProviderHealthRegistry:
    def __init__(self, *, failure_threshold: int = 2, cooldown_seconds: float = 30.0) -> None:
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._states: dict[tuple[str, str, str], _ProviderHealthState] = {}

    def is_available(self, config: _ResolvedConfig) -> bool:
        state = self._states.get(_provider_key(config))
        return state is None or state.cooldown_until <= time.monotonic()

    def record_success(self, config: _ResolvedConfig) -> None:
        self._states.pop(_provider_key(config), None)

    def record_failure(self, config: _ResolvedConfig, failure: _Failure) -> None:
        if failure.code not in {
            "AGENT_CAPACITY_EXCEEDED",
            "AGENT_MODEL_AUTH_FAILED",
            "AGENT_MODEL_INVALID_RESPONSE",
            "AGENT_MODEL_UNAVAILABLE",
        }:
            return
        state = self._states.setdefault(_provider_key(config), _ProviderHealthState())
        state.consecutive_failures += 1
        if state.consecutive_failures >= self._failure_threshold:
            state.cooldown_until = time.monotonic() + self._cooldown_seconds


_PROVIDER_HEALTH = _ProviderHealthRegistry()


class ConfiguredModelGateway:
    def __init__(self, *, tool_executor: ScopedToolExecutor | None = None) -> None:
        self._tool_executor = tool_executor

    async def generate(self, request: GenerationRequest) -> GeneratedAnswer:
        configs = self._resolve_configs(request)
        attempts: list[dict[str, Any]] = []
        last_failure = _Failure("AGENT_MODEL_UNAVAILABLE", False)
        provider_model_calls = 0
        available_configs = [
            config for config in configs if _PROVIDER_HEALTH.is_available(config)
        ]
        if available_configs:
            skipped_configs = [
                config for config in configs if config not in available_configs
            ]
            attempts.extend(
                _attempt(
                    config,
                    0,
                    "skipped",
                    "AGENT_PROVIDER_COOLDOWN",
                    reasoning_step=0,
                )
                for config in skipped_configs
            )
            configs = available_configs

        for config in configs:
            reasoning_summary = ""
            combined_evidence = list(request.evidence)
            tool_evidence = []
            tool_trace: list[dict[str, Any]] = []
            observations: list[dict[str, Any]] = []
            tool_call_count = 0
            remaining_output_tokens = min(
                settings.ANSWER_REASONING_TOTAL_OUTPUT_TOKENS,
                request.max_completion_tokens,
            )
            remaining_prompt_tokens = request.max_prompt_tokens
            prompt_tokens = 0
            completion_tokens = 0
            try:
                client = self._create_client(config)
            except RuntimeDependencyError as exc:
                last_failure = _Failure(exc.error_code, False)
                attempts.append(
                    _attempt(config, 1, "failed", last_failure.code, reasoning_step=1)
                )
                _PROVIDER_HEALTH.record_failure(config, last_failure)
                continue
            try:
                for reasoning_step in range(1, settings.ANSWER_REASONING_MAX_STEPS + 1):
                    budget = _prompt_budget(
                        config,
                        request.question,
                        request.conversation,
                        reasoning_summary,
                        reserve_evidence=request.mode != "general_chat",
                        output_token_limit=remaining_output_tokens,
                        input_token_limit=remaining_prompt_tokens,
                    )
                    messages = build_messages(
                        mode=request.mode,
                        question=budget.question,
                        evidence=combined_evidence,
                        conversation=request.conversation,
                        max_conversation_chars=budget.conversation_chars,
                        max_context_chars=budget.evidence_chars,
                        reasoning_summary=reasoning_summary,
                        max_reasoning_chars=budget.reasoning_chars,
                        step_index=reasoning_step,
                        max_steps=settings.ANSWER_REASONING_MAX_STEPS,
                        available_tools=(
                            available_tool_specs(request.tool_context)
                            if self._tool_executor is not None and request.tool_context is not None
                            else []
                        ),
                        tool_observations=bounded_observations(
                            observations,
                            max_chars=settings.ANSWER_TOOL_OBSERVATION_MAX_CHARS,
                        ),
                    )
                    step_completed = False
                    for attempt in range(1, settings.ANSWER_LLM_MAX_ATTEMPTS + 1):
                        if provider_model_calls >= request.max_model_calls:
                            raise RuntimeDependencyError("AGENT_CAPACITY_EXCEEDED")
                        provider_model_calls += 1
                        try:
                            response = await client.chat.completions.create(
                                model=config.model_name,
                                temperature=config.temperature,
                                max_tokens=budget.output_tokens,
                                messages=messages,
                                response_format={"type": "json_object"},
                            )
                            content = response.choices[0].message.content
                            if not isinstance(content, str) or not content:
                                raise ValueError("empty provider response")
                            parsed = _ProviderAnswer.model_validate(json.loads(content))
                            if parsed.decision == "tool" and (
                                self._tool_executor is None
                                or request.tool_context is None
                                or reasoning_step >= settings.ANSWER_REASONING_MAX_STEPS
                            ):
                                raise ValueError("tool decision is unavailable at this step")
                        except (ValidationError, ValueError, KeyError, IndexError, json.JSONDecodeError):
                            last_failure = _Failure("AGENT_MODEL_INVALID_RESPONSE", True)
                        except asyncio.CancelledError:
                            raise
                        except Exception as exc:
                            last_failure = _classify_provider_error(exc)
                        else:
                            usage = response.usage
                            step_prompt_tokens = max(0, int(usage.prompt_tokens)) if usage else 0
                            step_completion_tokens = (
                                max(0, int(usage.completion_tokens)) if usage else 0
                            )
                            prompt_tokens += step_prompt_tokens
                            completion_tokens += step_completion_tokens
                            remaining_prompt_tokens = max(
                                0,
                                remaining_prompt_tokens
                                - (
                                    step_prompt_tokens
                                    if usage
                                    else max(
                                        1,
                                        sum(
                                            len(str(message.get("content", "")))
                                            for message in messages
                                        )
                                        // 3,
                                    )
                                ),
                            )
                            charged_output_tokens = (
                                max(1, step_completion_tokens)
                                if usage
                                else budget.output_tokens
                            )
                            remaining_output_tokens = max(
                                0,
                                remaining_output_tokens - charged_output_tokens,
                            )
                            transition = transition_reasoning_step(
                                step_index=reasoning_step,
                                max_steps=settings.ANSWER_REASONING_MAX_STEPS,
                                decision="continue" if parsed.decision == "tool" else parsed.decision,
                                summary=parsed.reasoning_summary or "",
                                max_summary_chars=settings.ANSWER_REASONING_SUMMARY_MAX_CHARS,
                                budget_exhausted=remaining_output_tokens <= 0,
                            )
                            attempts.append(
                                _attempt(
                                    config,
                                    attempt,
                                    "completed",
                                    reasoning_step=reasoning_step,
                                    decision=parsed.decision,
                                    stop_reason=transition.stop_reason,
                                    tool_names=[item.name for item in parsed.tool_calls],
                                )
                            )
                            if (
                                prompt_tokens > request.max_prompt_tokens
                                or completion_tokens > request.max_completion_tokens
                            ):
                                raise RuntimeDependencyError("AGENT_CAPACITY_EXCEEDED")
                            if not transition.should_continue:
                                _PROVIDER_HEALTH.record_success(config)
                                return GeneratedAnswer(
                                    answer=parsed.answer,
                                    route=request.mode,
                                    citations=parsed.citations,
                                    confidence=parsed.confidence,
                                    uncertainty=parsed.uncertainty,
                                    insufficient_evidence=parsed.insufficient_evidence,
                                    prompt_tokens=prompt_tokens,
                                    completion_tokens=completion_tokens,
                                    cost=0,
                                    model_attempts=attempts,
                                    tool_calls=tool_trace,
                                    tool_evidence=tool_evidence,
                                    selected_provider=config.provider,
                                    selected_model=config.model_name,
                                    fallback_used=config.fallback,
                                    stop_reason=transition.stop_reason,
                                )
                            if parsed.decision == "tool":
                                for call_index, provider_call in enumerate(parsed.tool_calls, 1):
                                    call = ToolRequest.model_validate(provider_call.model_dump())
                                    tool_call_id = f"tool_{reasoning_step}_{call_index}"
                                    if tool_call_count >= settings.ANSWER_TOOL_MAX_CALLS:
                                        execution = budget_exceeded_execution(
                                            call,
                                            tool_call_id=tool_call_id,
                                        )
                                    else:
                                        tool_call_count += 1
                                        execution = await self._tool_executor.execute(
                                            call,
                                            context=request.tool_context,
                                            tool_call_id=tool_call_id,
                                        )
                                    tool_trace.append(execution.trace)
                                    observations.append(execution.observation)
                                    for item in execution.evidence:
                                        if all(
                                            existing.evidence_id != item.evidence_id
                                            for existing in combined_evidence
                                        ):
                                            combined_evidence.append(item)
                                            tool_evidence.append(item)
                            reasoning_summary = transition.summary
                            step_completed = True
                            break

                        attempts.append(
                            _attempt(
                                config,
                                attempt,
                                "failed",
                                last_failure.code,
                                reasoning_step=reasoning_step,
                            )
                        )
                        if (
                            not last_failure.retryable
                            or attempt == settings.ANSWER_LLM_MAX_ATTEMPTS
                        ):
                            break
                        await asyncio.sleep(
                            _retry_delay(attempt, last_failure.retry_after_seconds)
                        )
                    if not step_completed:
                        break
            finally:
                try:
                    await client.close()
                except Exception:
                    pass
            _PROVIDER_HEALTH.record_failure(config, last_failure)

        raise RuntimeDependencyError(last_failure.code)

    @staticmethod
    def _resolve_configs(request: GenerationRequest) -> list[_ResolvedConfig]:
        configs = [_primary_config(request.model)]
        if request.allow_model_fallback and settings.ANSWER_LLM_FALLBACK_MODEL.strip():
            fallback = _fallback_config()
            primary = configs[0]
            if (fallback.provider, fallback.base_url, fallback.model_name) != (
                primary.provider,
                primary.base_url,
                primary.model_name,
            ):
                configs.append(fallback)
        return configs

    @staticmethod
    def _create_client(config: _ResolvedConfig):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise RuntimeDependencyError("AGENT_MODEL_UNAVAILABLE") from None

        api_key = config.api_key.get_secret_value()
        if not api_key:
            raise RuntimeDependencyError("AGENT_MODEL_UNAVAILABLE")
        kwargs: dict[str, Any] = {
            "api_key": api_key,
            "base_url": config.base_url or None,
            "max_retries": 0,
            "timeout": None,
        }
        if config.provider == "mimo":
            kwargs["default_headers"] = {"api-key": api_key}
        try:
            return AsyncOpenAI(**kwargs)
        except Exception:
            raise RuntimeDependencyError("AGENT_MODEL_UNAVAILABLE") from None


def _primary_config(model: ModelInvocationConfig | None) -> _ResolvedConfig:
    if model is not None:
        if not model.model_name.strip():
            raise RuntimeDependencyError("AGENT_MODEL_UNAVAILABLE")
        return _ResolvedConfig(
            provider=model.provider.strip().lower(),
            base_url=model.base_url.strip(),
            model_name=model.model_name.strip(),
            temperature=model.temperature,
            context_window=model.context_window,
            api_key=model.api_key,
        )
    if not settings.ANSWER_LLM_MODEL.strip():
        raise RuntimeDependencyError("AGENT_MODEL_UNAVAILABLE")
    return _ResolvedConfig(
        provider=settings.ANSWER_LLM_PROVIDER.strip().lower(),
        base_url=settings.ANSWER_LLM_BASE_URL.strip(),
        model_name=settings.ANSWER_LLM_MODEL.strip(),
        temperature=settings.ANSWER_LLM_TEMPERATURE,
        context_window=settings.ANSWER_LLM_CONTEXT_WINDOW,
        api_key=settings.ANSWER_LLM_API_KEY,
    )


def _fallback_config() -> _ResolvedConfig:
    return _ResolvedConfig(
        provider=settings.ANSWER_LLM_FALLBACK_PROVIDER.strip().lower() or "openai",
        base_url=settings.ANSWER_LLM_FALLBACK_BASE_URL.strip(),
        model_name=settings.ANSWER_LLM_FALLBACK_MODEL.strip(),
        temperature=settings.ANSWER_LLM_FALLBACK_TEMPERATURE,
        context_window=settings.ANSWER_LLM_FALLBACK_CONTEXT_WINDOW,
        api_key=settings.ANSWER_LLM_FALLBACK_API_KEY,
        fallback=True,
    )


def _provider_key(config: _ResolvedConfig) -> tuple[str, str, str]:
    return config.provider, config.base_url, config.model_name


def _classify_provider_error(exc: Exception) -> _Failure:
    status_code = getattr(exc, "status_code", None)
    if status_code in {401, 403}:
        return _Failure("AGENT_MODEL_AUTH_FAILED", False)
    if status_code == 429:
        return _Failure("AGENT_CAPACITY_EXCEEDED", True, _retry_after(exc))
    if isinstance(status_code, int) and status_code >= 500:
        return _Failure("AGENT_MODEL_UNAVAILABLE", True, _retry_after(exc))
    error_name = type(exc).__name__.lower()
    if any(token in error_name for token in ("timeout", "connection", "connect", "network")):
        return _Failure("AGENT_MODEL_UNAVAILABLE", True)
    return _Failure("AGENT_MODEL_UNAVAILABLE", False)


def _retry_after(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    try:
        value = float(headers.get("Retry-After", ""))
    except (TypeError, ValueError):
        return None
    return max(0.0, min(value, settings.ANSWER_LLM_RETRY_MAX_SECONDS))


def _retry_delay(attempt: int, retry_after_seconds: float | None) -> float:
    if retry_after_seconds is not None:
        return retry_after_seconds
    return min(
        settings.ANSWER_LLM_RETRY_BASE_SECONDS * (2 ** (attempt - 1)),
        settings.ANSWER_LLM_RETRY_MAX_SECONDS,
    )


def _attempt(
    config: _ResolvedConfig,
    attempt: int,
    status: str,
    error_code: str | None = None,
    *,
    reasoning_step: int = 1,
    decision: str | None = None,
    stop_reason: str | None = None,
    tool_names: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "provider": config.provider,
        "model": config.model_name,
        "attempt": attempt,
        "fallback": config.fallback,
        "status": status,
        "reasoning_step": reasoning_step,
        **({"error_code": error_code} if error_code else {}),
        **({"decision": decision} if decision else {}),
        **({"stop_reason": stop_reason} if stop_reason else {}),
        **({"tool_names": tool_names} if tool_names else {}),
    }


def _prompt_budget(
    config: _ResolvedConfig,
    question: str,
    conversation: ConversationContextData,
    reasoning_summary: str = "",
    *,
    reserve_evidence: bool,
    output_token_limit: int | None = None,
    input_token_limit: int | None = None,
) -> _PromptBudget:
    per_call_output_tokens = min(
        settings.ANSWER_MAX_OUTPUT_TOKENS,
        max(128, config.context_window // 4),
    )
    output_tokens = min(
        per_call_output_tokens,
        max(1, output_token_limit) if output_token_limit is not None else per_call_output_tokens,
    )
    input_tokens = max(0, config.context_window - output_tokens)
    if input_token_limit is not None:
        input_tokens = min(input_tokens, max(0, input_token_limit))
    prompt_reserve = min(
        settings.ANSWER_PROMPT_RESERVE_TOKENS,
        max(128, input_tokens // 4),
    )
    usable_input_chars = max(
        0,
        int((input_tokens - prompt_reserve) * settings.ANSWER_CONTEXT_CHARS_PER_TOKEN),
    )
    question_limit = usable_input_chars // 3 if reserve_evidence else usable_input_chars
    bounded_question = question[: min(settings.ANSWER_MAX_QUESTION_CHARS, question_limit)]
    remaining_chars = max(0, usable_input_chars - len(bounded_question))
    available_conversation_chars = len(conversation.summary) + sum(
        len(message.content) for message in conversation.messages
    )
    supplemental_limit = remaining_chars // 3 if reserve_evidence else remaining_chars
    reasoning_limit = supplemental_limit if reserve_evidence else remaining_chars // 3
    reasoning_chars = min(len(reasoning_summary), reasoning_limit)
    conversation_limit = max(0, supplemental_limit - reasoning_chars)
    conversation_chars = min(available_conversation_chars, conversation_limit)
    evidence_chars = min(
        settings.ANSWER_MAX_CONTEXT_CHARS,
        max(0, remaining_chars - reasoning_chars - conversation_chars)
        if reserve_evidence
        else 0,
    )
    return _PromptBudget(
        question=bounded_question,
        reasoning_chars=reasoning_chars,
        conversation_chars=conversation_chars,
        evidence_chars=evidence_chars,
        output_tokens=output_tokens,
    )
