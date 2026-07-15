import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from services.memory_agent.config import settings
from services.memory_agent.contracts.common import ModelInvocationConfig
from services.memory_agent.runtime.contracts import GeneratedAnswer, GenerationRequest
from services.memory_agent.runtime.orchestrator import RuntimeDependencyError
from services.memory_agent.runtime.prompts import build_messages


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
    api_key_source: ModelInvocationConfig | None


class ConfiguredModelGateway:
    async def generate(self, request: GenerationRequest) -> GeneratedAnswer:
        config = self._resolve_config(request.model)
        messages = build_messages(
            mode=request.mode,
            question=request.question[: settings.ANSWER_MAX_QUESTION_CHARS],
            evidence=request.evidence,
            max_context_chars=settings.ANSWER_MAX_CONTEXT_CHARS,
        )
        client = self._create_client(config)
        try:
            response = await client.chat.completions.create(
                model=config.model_name,
                temperature=config.temperature,
                max_tokens=settings.ANSWER_MAX_OUTPUT_TOKENS,
                messages=messages,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not isinstance(content, str) or not content:
                raise ValueError("empty provider response")
            parsed = _ProviderAnswer.model_validate(json.loads(content))
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
            )
        except (ValidationError, ValueError, KeyError, IndexError, json.JSONDecodeError):
            raise RuntimeDependencyError("AGENT_MODEL_UNAVAILABLE") from None
        except RuntimeDependencyError:
            raise
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code == 429:
                raise RuntimeDependencyError("AGENT_CAPACITY_EXCEEDED") from None
            raise RuntimeDependencyError("AGENT_MODEL_UNAVAILABLE") from None
        finally:
            try:
                await client.close()
            except Exception:
                pass

    @staticmethod
    def _resolve_config(model: ModelInvocationConfig | None) -> _ResolvedConfig:
        if model is not None:
            if not model.model_name.strip():
                raise RuntimeDependencyError("AGENT_MODEL_UNAVAILABLE")
            return _ResolvedConfig(
                provider=model.provider.strip().lower(),
                base_url=model.base_url.strip(),
                model_name=model.model_name.strip(),
                temperature=model.temperature,
                api_key_source=model,
            )
        if not settings.ANSWER_LLM_MODEL:
            raise RuntimeDependencyError("AGENT_MODEL_UNAVAILABLE")
        return _ResolvedConfig(
            provider=settings.ANSWER_LLM_PROVIDER.strip().lower(),
            base_url=settings.ANSWER_LLM_BASE_URL.strip(),
            model_name=settings.ANSWER_LLM_MODEL.strip(),
            temperature=settings.ANSWER_LLM_TEMPERATURE,
            api_key_source=None,
        )

    @staticmethod
    def _create_client(config: _ResolvedConfig):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise RuntimeDependencyError("AGENT_MODEL_UNAVAILABLE") from None

        # SecretStr is revealed only here, at the provider constructor boundary.
        api_key = (
            config.api_key_source.api_key.get_secret_value()
            if config.api_key_source is not None
            else settings.ANSWER_LLM_API_KEY.get_secret_value()
        )
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
