import asyncio
import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, SecretStr, ValidationError

from app.mneme.memoria.server.config import settings
from app.mneme.memoria.server.contracts.common import ModelInvocationConfig
from app.mneme.memoria.server.runtime.contracts import GeneratedAnswer, GenerationRequest
from app.mneme.memoria.server.runtime.orchestrator import RuntimeDependencyError
from app.mneme.memoria.server.runtime.prompts import build_messages


class _ProviderAnswer(BaseModel):
    answer: str = Field(max_length=20000)
    citations: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    confidence: float = Field(ge=0, le=1)
    uncertainty: str | None = Field(default=None, max_length=2000)
    insufficient_evidence: bool = False


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
    evidence_chars: int
    output_tokens: int


class ConfiguredModelGateway:
    async def generate(self, request: GenerationRequest) -> GeneratedAnswer:
        configs = self._resolve_configs(request)
        attempts: list[dict[str, Any]] = []
        last_failure = _Failure("AGENT_MODEL_UNAVAILABLE", False)

        for config in configs:
            budget = _prompt_budget(
                config,
                request.question,
                reserve_evidence=request.mode != "general_chat",
            )
            messages = build_messages(
                mode=request.mode,
                question=budget.question,
                evidence=request.evidence,
                max_context_chars=budget.evidence_chars,
            )
            try:
                client = self._create_client(config)
            except RuntimeDependencyError as exc:
                last_failure = _Failure(exc.error_code, False)
                attempts.append(_attempt(config, 1, "failed", last_failure.code))
                continue
            try:
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
                        attempts.append(_attempt(config, attempt, "completed"))
                        usage = response.usage
                        return GeneratedAnswer(
                            answer=parsed.answer,
                            route=request.mode,
                            citations=parsed.citations,
                            confidence=parsed.confidence,
                            uncertainty=parsed.uncertainty,
                            insufficient_evidence=parsed.insufficient_evidence,
                            prompt_tokens=max(0, int(usage.prompt_tokens)) if usage else 0,
                            completion_tokens=max(0, int(usage.completion_tokens)) if usage else 0,
                            cost=0,
                            model_attempts=attempts,
                            selected_provider=config.provider,
                            selected_model=config.model_name,
                            fallback_used=config.fallback,
                        )

                    attempts.append(_attempt(config, attempt, "failed", last_failure.code))
                    if not last_failure.retryable or attempt == settings.ANSWER_LLM_MAX_ATTEMPTS:
                        break
                    await asyncio.sleep(_retry_delay(attempt, last_failure.retry_after_seconds))
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
) -> dict[str, Any]:
    return {
        "provider": config.provider,
        "model": config.model_name,
        "attempt": attempt,
        "fallback": config.fallback,
        "status": status,
        **({"error_code": error_code} if error_code else {}),
    }


def _prompt_budget(
    config: _ResolvedConfig,
    question: str,
    *,
    reserve_evidence: bool,
) -> _PromptBudget:
    output_tokens = min(
        settings.ANSWER_MAX_OUTPUT_TOKENS,
        max(128, config.context_window // 4),
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
    question_budget = usable_input_chars // 3 if reserve_evidence else usable_input_chars
    bounded_question = question[: min(settings.ANSWER_MAX_QUESTION_CHARS, question_budget)]
    evidence_chars = min(
        settings.ANSWER_MAX_CONTEXT_CHARS,
        max(0, usable_input_chars - len(bounded_question)),
    )
    return _PromptBudget(
        question=bounded_question,
        evidence_chars=evidence_chars,
        output_tokens=output_tokens,
    )
