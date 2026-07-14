import json

from pydantic import ValidationError

from services.memory_agent.config import settings
from services.memory_agent.memory.schemas import (
    EvidenceInput,
    ExtractedCandidate,
    ExtractionResponse,
)
from services.memory_agent.memory.sensitivity import contains_secret


class ExtractionUnavailable(RuntimeError):
    pass


async def extract_candidates(evidence: EvidenceInput) -> list[ExtractedCandidate]:
    # This must remain before client construction and every external model call.
    if contains_secret(evidence.excerpt):
        return []
    api_key = settings.EXTRACTION_LLM_API_KEY.get_secret_value()
    if not api_key or not settings.EXTRACTION_LLM_MODEL:
        raise ExtractionUnavailable("memory extraction model is not configured")

    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise ExtractionUnavailable("memory extraction client is unavailable") from exc
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=settings.EXTRACTION_LLM_BASE_URL or None,
    )
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
                    "strict": False,
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
        raise ExtractionUnavailable("memory extraction returned invalid structured output") from None
    except ExtractionUnavailable:
        raise
    except Exception:
        raise ExtractionUnavailable("memory extraction model request failed") from None
    finally:
        await client.close()
