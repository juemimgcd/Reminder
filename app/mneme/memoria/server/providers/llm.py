import asyncio
import json
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


class _ProviderAnswer(BaseModel):
    decision: Literal["continue", "final"] = "final"
    reasoning_summary: str | None = Field(default=None, max_length=2000)
    answer: str = Field(min_length=1, max_length=20000)
    citations: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    confidence: float = Field(ge=0, le=1)
    uncertainty: str | None = Field(default=None, max_length=2000)
    insufficient_evidence: bool = False

    @model_validator(mode="after")
    def continuing_requires_summary(self) -> "_ProviderAnswer":
        if self.decision == "continue" and not (self.reasoning_summary or "").strip():
            raise ValueError("reasoning_summary is required when decision is continue")
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


class ConfiguredModelGateway:
    async def generate(self, request: GenerationRequest) -> GeneratedAnswer:
        configs = self._resolve_configs(request)
        attempts: list[dict[str, Any]] = []
        last_failure = _Failure("AGENT_MODEL_UNAVAILABLE", False)

        for config in configs:
            reasoning_summary = ""
            remaining_output_tokens = settings.ANSWER_REASONING_TOTAL_OUTPUT_TOKENS
            prompt_tokens = 0
            completion_tokens = 0
            try:
                client = self._create_client(config)
            except RuntimeDependencyError as exc:
                last_failure = _Failure(exc.error_code, False)
                attempts.append(
                    _attempt(config, 1, "failed", last_failure.code, reasoning_step=1)
                )
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
                    )
                    messages = build_messages(
                        mode=request.mode,
                        question=budget.question,
                        evidence=request.evidence,
                        conversation=request.conversation,
                        max_conversation_chars=budget.conversation_chars,
                        max_context_chars=budget.evidence_chars,
                        reasoning_summary=reasoning_summary,
                        max_reasoning_chars=budget.reasoning_chars,
                        step_index=reasoning_step,
                        max_steps=settings.ANSWER_REASONING_MAX_STEPS,
                    )
                    step_completed = False
                    for attempt in range(1, settings.ANSWER_LLM_MAX_ATTEMPTS + 1):
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
                                decision=parsed.decision,
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
                                )
                            )
                            if not transition.should_continue:
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
                                    selected_provider=config.provider,
                                    selected_model=config.model_name,
                                    fallback_used=config.fallback,
                                )
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
    }


def _prompt_budget(
    config: _ResolvedConfig,
    question: str,
    conversation: ConversationContextData,
    reasoning_summary: str = "",
    *,
    reserve_evidence: bool,
    output_token_limit: int | None = None,
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
