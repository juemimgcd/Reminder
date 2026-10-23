"""Provide retrying, fallback-aware LLM access for Memoria generation phases.

Provider attempts are observable without logging prompts, answers, credentials, or hidden reasoning.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr, ValidationError, model_validator

from app.mneme.memoria.server.config import settings
from app.mneme.memoria.server.contracts.answers import ConversationContextData
from app.mneme.memoria.server.contracts.common import ModelInvocationConfig
from app.mneme.memoria.server.runtime.agentic import RetrievalAssessment
from app.mneme.memoria.server.runtime.citations import resolve_citations
from app.mneme.memoria.server.runtime.contracts import GeneratedAnswer, GenerationRequest
from app.mneme.memoria.server.runtime.grounding import INSUFFICIENT_EVIDENCE_ANSWER
from app.mneme.memoria.server.runtime.orchestrator import RuntimeDependencyError
from app.mneme.memoria.server.runtime.prompts import build_messages, context_evidence
from app.mneme.memoria.server.runtime.reasoning import transition_reasoning_step
from app.mneme.memoria.server.runtime.tools import (
    ScopedToolExecutor,
    ToolRequest,
    available_tool_specs,
    bounded_observations,
    budget_exceeded_execution,
    execute_with_timeout,
    read_call_key,
    repeated_search_execution,
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
    retrieval_assessment: RetrievalAssessment | None = None

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
    """Generate answers through configured primary and fallback model routes.

    The gateway owns provider retries, cooldown-aware route order, timeout
    classification, usage aggregation, and privacy-safe attempt metadata.
    """
    def __init__(self, *, tool_executor: ScopedToolExecutor | None = None) -> None:
        self._tool_executor = tool_executor

    async def generate(self, request: GenerationRequest) -> GeneratedAnswer:
        """Run bounded retrieval and generation with one budget across providers.

        Evidence requirements and search queries live only in this invocation.
        Persisted attempts contain counts and decisions, never the plan's text.
        """
        configs = self._resolve_configs(request)
        attempts: list[dict[str, Any]] = []
        last_failure = _Failure("AGENT_MODEL_UNAVAILABLE", False)
        provider_model_calls = 0
        reasoning_steps_used = 0
        reasoning_summary = ""
        combined_evidence = list(request.evidence)
        tool_evidence = []
        tool_trace: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        completed_searches: set[tuple[str, str, int]] = set()
        tool_call_count = 0
        assessment: RetrievalAssessment | None = None
        agentic = request.mode != "general_chat" and request.execution_mode == "single"
        remaining_output_tokens = min(
            settings.ANSWER_REASONING_TOTAL_OUTPUT_TOKENS, request.max_completion_tokens,
        )
        remaining_prompt_tokens = request.max_prompt_tokens
        prompt_tokens = 0
        completion_tokens = 0
        usage_estimated = False
        available_configs = [config for config in configs if _PROVIDER_HEALTH.is_available(config)]
        if available_configs:
            attempts.extend(
                _attempt(config, 0, "skipped", "AGENT_PROVIDER_COOLDOWN", reasoning_step=0)
                for config in configs if config not in available_configs
            )
            configs = available_configs

        for config_index, config in enumerate(configs):
            has_fallback = config_index + 1 < len(configs)
            try:
                client = self._create_client(config)
            except RuntimeDependencyError as exc:
                last_failure = _Failure(exc.error_code, False)
                attempts.append(_attempt(config, 0, "failed", last_failure.code, reasoning_step=0))
                _PROVIDER_HEALTH.record_failure(config, last_failure)
                continue
            try:
                for reasoning_step in range(reasoning_steps_used + 1, settings.ANSWER_REASONING_MAX_STEPS + 1):
                    step_completed = False
                    for attempt in range(1, settings.ANSWER_LLM_MAX_ATTEMPTS + 1):
                        if (
                            provider_model_calls >= request.max_model_calls
                            or remaining_output_tokens <= 0
                            or remaining_prompt_tokens <= 0
                        ):
                            raise RuntimeDependencyError("AGENT_CAPACITY_EXCEEDED")
                        budget = _prompt_budget(
                            config, request.question, request.conversation, reasoning_summary,
                            reserve_evidence=request.mode != "general_chat",
                            output_token_limit=remaining_output_tokens,
                            input_token_limit=remaining_prompt_tokens,
                        )
                        tools = (
                            available_tool_specs(request.tool_context)
                            if self._tool_executor is not None and request.tool_context is not None
                            and tool_call_count < settings.ANSWER_TOOL_MAX_CALLS
                            and reasoning_step < settings.ANSWER_REASONING_MAX_STEPS
                            and provider_model_calls + 1 < request.max_model_calls
                            else []
                        )
                        progress = assessment.model_dump_json() if assessment else ""
                        # Account for tools/progress as well as evidence. Byte counts are a
                        # conservative estimate when a provider tokenizer is unavailable.
                        context_chars = budget.evidence_chars
                        conversation_chars = budget.conversation_chars
                        while True:
                            visible_evidence = context_evidence(
                                combined_evidence, max_context_chars=context_chars,
                            )
                            messages = build_messages(
                                mode=request.mode, question=budget.question,
                                evidence=visible_evidence, conversation=request.conversation,
                                max_conversation_chars=conversation_chars,
                                max_context_chars=context_chars,
                                reasoning_summary=reasoning_summary,
                                max_reasoning_chars=budget.reasoning_chars,
                                step_index=reasoning_step,
                                max_steps=settings.ANSWER_REASONING_MAX_STEPS,
                                available_tools=tools,
                                tool_observations=bounded_observations(
                                    observations, max_chars=settings.ANSWER_TOOL_OBSERVATION_MAX_CHARS,
                                ),
                                grounding_requirement=request.grounding_requirement,
                                agentic_retrieval=agentic, retrieval_progress=progress,
                            )
                            estimated_input = sum(
                                len(message["content"].encode("utf-8")) + 8 for message in messages
                            )
                            if estimated_input <= min(
                                remaining_prompt_tokens, config.context_window - budget.output_tokens,
                            ):
                                break
                            if not context_chars and not conversation_chars:
                                raise RuntimeDependencyError("AGENT_CAPACITY_EXCEEDED")
                            context_chars //= 2
                            conversation_chars //= 2
                        provider_model_calls += 1
                        charged_prompt = estimated_input
                        charged_completion = budget.output_tokens
                        response_usage_known = False
                        response_received = False
                        explicit_provider_rejection = False
                        try:
                            response = await client.chat.completions.create(
                                model=config.model_name, temperature=config.temperature,
                                max_tokens=budget.output_tokens, messages=messages,
                                response_format={"type": "json_object"},
                            )
                            response_received = True
                            # Charge every response, including malformed JSON and retries.
                            usage = response.usage
                            if usage is not None:
                                charged_prompt = max(0, int(usage.prompt_tokens))
                                charged_completion = max(0, int(usage.completion_tokens))
                                response_usage_known = True
                            content = response.choices[0].message.content
                            if not isinstance(content, str) or not content:
                                raise ValueError("empty provider response")
                            parsed = _ProviderAnswer.model_validate(json.loads(content))
                            next_assessment = assessment
                            if agentic:
                                if parsed.retrieval_assessment is None:
                                    raise ValueError("private answers require a retrieval assessment")
                                next_assessment = parsed.retrieval_assessment.reconcile(
                                    assessment,
                                    visible_evidence_ids={item.evidence_id for item in visible_evidence},
                                )
                            if parsed.decision == "tool" and (
                                self._tool_executor is None or request.tool_context is None
                            ):
                                raise ValueError("tools are unavailable for this request")
                        except (ValidationError, ValueError, KeyError, IndexError, json.JSONDecodeError):
                            last_failure = _Failure("AGENT_MODEL_INVALID_RESPONSE", True)
                            observations.append({
                                "status": "rejected",
                                "message": (
                                    "Response did not satisfy the output contract. Return valid JSON, "
                                    "preserve requirement IDs/questions, and reference only visible evidence."
                                ),
                            })
                        except asyncio.CancelledError:
                            raise
                        except Exception as exc:
                            last_failure = _classify_provider_error(exc)
                            status_code = getattr(exc, "status_code", None)
                            if not response_received and isinstance(status_code, int) and 400 <= status_code < 600:
                                # An HTTP rejection has no completion to charge. It still
                                # consumes a model call and the enclosing time budget.
                                charged_prompt = 0
                                charged_completion = 0
                                explicit_provider_rejection = True
                        else:
                            step_completed = True
                        finally:
                            usage_estimated = usage_estimated or not response_usage_known
                            prompt_tokens += charged_prompt
                            completion_tokens += charged_completion
                            remaining_prompt_tokens = max(0, remaining_prompt_tokens - charged_prompt)
                            remaining_output_tokens = max(0, remaining_output_tokens - charged_completion)

                        if prompt_tokens > request.max_prompt_tokens or completion_tokens > min(
                            request.max_completion_tokens, settings.ANSWER_REASONING_TOTAL_OUTPUT_TOKENS,
                        ):
                            raise RuntimeDependencyError("AGENT_CAPACITY_EXCEEDED")
                        if step_completed:
                            assessment = next_assessment
                            reasoning_steps_used = reasoning_step
                            valid_citations = resolve_citations(parsed.citations, visible_evidence)
                            cited_ids = {item["evidence_id"] for item in valid_citations}
                            coverage_ok = assessment is None or assessment.covered_by(cited_ids)
                            # A premature final with missing support gets a bounded repair
                            # round. It cannot silently remove the unresolved requirements.
                            decision = "continue" if parsed.decision == "tool" else parsed.decision
                            if agentic and not coverage_ok and parsed.decision == "final" and (
                                tools or (assessment is not None and assessment.sufficient)
                            ):
                                decision = "continue"
                            exhausted = (
                                remaining_output_tokens <= 0 or remaining_prompt_tokens <= 0
                                or provider_model_calls >= request.max_model_calls
                            )
                            transition = transition_reasoning_step(
                                step_index=reasoning_step, max_steps=settings.ANSWER_REASONING_MAX_STEPS,
                                decision=decision,
                                summary=parsed.reasoning_summary or "Evidence coverage or citations need review.",
                                max_summary_chars=settings.ANSWER_REASONING_SUMMARY_MAX_CHARS,
                                budget_exhausted=exhausted,
                            )
                            attempts.append({
                                **_attempt(
                                    config, attempt, "completed", reasoning_step=reasoning_step,
                                    decision=parsed.decision, stop_reason=transition.stop_reason,
                                    tool_names=[item.name for item in parsed.tool_calls],
                                ),
                                **({
                                    "requirement_count": len(assessment.requirements),
                                    "missing_requirement_count": assessment.missing_count,
                                    "coverage_satisfied": coverage_ok,
                                } if assessment is not None else {}),
                            })
                            if not transition.should_continue:
                                # This applies to general chat and explicit multi mode too:
                                # their intermediate answer may be only a progress note.
                                if parsed.decision != "final":
                                    raise RuntimeDependencyError("AGENT_CAPACITY_EXCEEDED")
                                unsupported = agentic and (
                                    not coverage_ok or parsed.insufficient_evidence
                                )
                                _PROVIDER_HEALTH.record_success(config)
                                return GeneratedAnswer(
                                    answer=INSUFFICIENT_EVIDENCE_ANSWER if unsupported else parsed.answer,
                                    route=request.mode,
                                    citations=[] if unsupported else parsed.citations,
                                    confidence=min(parsed.confidence, 0.25) if unsupported else parsed.confidence,
                                    uncertainty=(
                                        "Evidence coverage is incomplete or could not be verified within the budget."
                                        if unsupported else parsed.uncertainty
                                    ),
                                    insufficient_evidence=unsupported or parsed.insufficient_evidence,
                                    prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, cost=0,
                                    model_attempts=attempts, tool_calls=tool_trace, tool_evidence=tool_evidence,
                                    required_citation_groups=(
                                        [item.evidence_ids for item in assessment.requirements]
                                        if assessment is not None and not unsupported else []
                                    ),
                                    selected_provider=config.provider, selected_model=config.model_name,
                                    fallback_used=config.fallback,
                                    stop_reason=(
                                        "insufficient_evidence"
                                        if unsupported and transition.stop_reason == "model_final"
                                        else transition.stop_reason
                                    ),
                                    budget_usage={
                                        "model_calls": provider_model_calls, "tool_calls": tool_call_count,
                                        "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                                        "usage_estimated": usage_estimated, "reasoning_steps": reasoning_steps_used,
                                        "retrieval_requirements": len(assessment.requirements) if assessment else 0,
                                        "missing_requirements": assessment.missing_count if assessment else 0,
                                    },
                                )
                            if parsed.decision == "tool":
                                for call_index, provider_call in enumerate(parsed.tool_calls, 1):
                                    call = ToolRequest.model_validate(provider_call.model_dump())
                                    tool_call_id = f"tool_{reasoning_step}_{call_index}"
                                    if tool_call_count >= settings.ANSWER_TOOL_MAX_CALLS:
                                        observations.append(budget_exceeded_execution(
                                            call, tool_call_id=tool_call_id,
                                        ).observation)
                                        break
                                    tool_call_count += 1
                                    key = read_call_key(call, context=request.tool_context)
                                    if key is not None and key in completed_searches:
                                        execution = repeated_search_execution(call, tool_call_id=tool_call_id)
                                    else:
                                        execution = await execute_with_timeout(
                                            self._tool_executor, call, context=request.tool_context,
                                            tool_call_id=tool_call_id,
                                        )
                                        if key is not None and execution.trace["status"] == "completed":
                                            completed_searches.add(key)
                                    tool_trace.append(execution.trace)
                                    observations.append(execution.observation)
                                    known = {item.evidence_id: item for item in combined_evidence}
                                    # Prioritize this lookup, retaining previously obtained facts
                                    # for dependent questions and avoiding duplicate evidence IDs.
                                    front = {item.evidence_id: known.get(item.evidence_id, item)
                                             for item in execution.evidence}
                                    tool_evidence.extend(item for key, item in front.items() if key not in known)
                                    combined_evidence = [*front.values(), *[
                                        item for item in combined_evidence if item.evidence_id not in front
                                    ]]
                            reasoning_summary = transition.summary
                            if agentic and not coverage_ok and parsed.decision == "final":
                                reasoning_summary = (
                                    "Resolve remaining evidence gaps with the allowed tools, then cite "
                                    "at least one supporting evidence ID for every requirement."
                                )
                            break

                        attempts.append(_attempt(
                            config, attempt, "failed", last_failure.code, reasoning_step=reasoning_step,
                        ))
                        if not last_failure.retryable or attempt == settings.ANSWER_LLM_MAX_ATTEMPTS:
                            break
                        # Do not spend the last available attempt on the failing route.
                        # A transport failure with unknown usage is charged conservatively;
                        # switch routes now instead of repeatedly consuming the same reserve.
                        if has_fallback and (
                            request.max_model_calls - provider_model_calls <= 1
                            or (not response_usage_known and not explicit_provider_rejection)
                            or remaining_output_tokens <= charged_completion
                            or remaining_prompt_tokens <= charged_prompt
                        ):
                            break
                        await asyncio.sleep(_retry_delay(attempt, last_failure.retry_after_seconds))
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
