import json

from pydantic import ValidationError

from services.memory_agent.config import settings
from services.memory_agent.memory.schemas import (
    EvidenceInput,
    ExtractedCandidate,
    ExtractionResponse,
)
from services.memory_agent.memory.sensitivity import contains_secret


class TerminalExtractionError(RuntimeError):
    pass


class RetryableExtractionError(RuntimeError):
    pass


_RETRYABLE_PROVIDER_ERRORS = frozenset(
    {
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "InternalServerError",
    }
)


def _raise_provider_error(exc: Exception) -> None:
    status_code = getattr(exc, "status_code", None)
    if (
        type(exc).__name__ in _RETRYABLE_PROVIDER_ERRORS
        or isinstance(status_code, int)
        and (status_code in {408, 429} or status_code >= 500)
    ):
        raise RetryableExtractionError("memory extraction provider is temporarily unavailable") from None
    raise TerminalExtractionError("memory extraction provider rejected the request") from None


async def extract_candidates(evidence: EvidenceInput) -> list[ExtractedCandidate]:
    # This must remain before client construction and every external model call.
    if contains_secret(evidence.excerpt):
        return []
    api_key = settings.EXTRACTION_LLM_API_KEY.get_secret_value()
    if not api_key or not settings.EXTRACTION_LLM_MODEL:
        raise TerminalExtractionError("memory extraction model is not configured")

    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise TerminalExtractionError("memory extraction client is unavailable") from None
    try:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.EXTRACTION_LLM_BASE_URL or None,
        )
    except Exception:
        raise TerminalExtractionError("memory extraction client configuration is invalid") from None
    schema = ExtractionResponse.model_json_schema(by_alias=True)
    try:
        response = await client.chat.completions.create(
            model=settings.EXTRACTION_LLM_MODEL,
            temperature=settings.EXTRACTION_LLM_TEMPERATURE,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract only durable user memories explicitly supported by the excerpt. "
                        "Use only the fixed schema types. Copy an exact supporting quote and its "
                        "zero-based start/end offsets. Do not decide persistence or status. Return JSON."
                    ),
                },
                {"role": "user", "content": evidence.excerpt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "memory_extraction",
                    "strict": True,
                    "schema": schema,
                },
            },
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("empty extraction response")
        extracted = ExtractionResponse.model_validate(json.loads(content))
        for candidate in extracted.candidates:
            candidate.validate_evidence(evidence.excerpt)
        return extracted.candidates
    except (ValidationError, ValueError, KeyError, IndexError):
        raise TerminalExtractionError("memory extraction returned invalid structured output") from None
    except (TerminalExtractionError, RetryableExtractionError):
        raise
    except Exception as exc:
        _raise_provider_error(exc)
    finally:
        try:
            await client.close()
        except Exception:
            pass
