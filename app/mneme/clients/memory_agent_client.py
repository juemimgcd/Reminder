import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt

from app.mneme.conf.config import settings
from app.mneme.schemas.memory_agent import (
    EventReceipt,
    MemoryAgentAnswerRequest,
    MemoryAgentAnswerResponse,
    MemoryAgentEvent,
)
from app.mneme.utils.exceptions import BusinessException

SERVICE_TOKEN_ALGORITHM = "HS256"
SERVICE_TOKEN_AUDIENCE = "memory-agent"
SERVICE_TOKEN_ISSUER = "mneme-backend"
MAX_SERVICE_TOKEN_LIFETIME = timedelta(minutes=5)
RETRYABLE_STATUS_CODES = {502, 503, 504}
MAX_ERROR_DETAIL_LENGTH = 1000
_REDACTED_RESPONSE_KEYS = {"body", "content", "input", "payload", "question", "source", "text"}


class MemoryAgentUnavailable(BusinessException):
    def __init__(self, message: str, *, status_code: int = 503):
        super().__init__(message=message, code=5032, status_code=status_code)

    def __str__(self) -> str:
        return self.message


class MemoryAgentRejected(BusinessException):
    def __init__(self, message: str, *, status_code: int):
        super().__init__(message=message, code=4025, status_code=status_code)

    def __str__(self) -> str:
        return self.message


class MemoryAgentClient:
    def __init__(self) -> None:
        timeout = httpx.Timeout(float(settings.MEMORY_AGENT_TIMEOUT_SECONDS))
        self._client = httpx.AsyncClient(
            base_url=settings.MEMORY_AGENT_BASE_URL.rstrip("/"),
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    async def __aenter__(self) -> "MemoryAgentClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def submit_event(self, event: MemoryAgentEvent) -> EventReceipt:
        response = await self._post_json(
            path="/internal/v1/events",
            payload=event.model_dump(mode="json"),
            request_id=event.event_id,
            scope="events:write",
        )
        try:
            return EventReceipt.model_validate(response.json())
        except ValueError as exc:
            raise MemoryAgentUnavailable("memory agent returned an invalid event receipt") from exc

    async def create_answer(self, request: MemoryAgentAnswerRequest) -> MemoryAgentAnswerResponse:
        response = await self._post_json(
            path="/v1/answers",
            payload=_answer_request_payload(request),
            request_id=request.request_id,
            scope="answers:write",
        )
        try:
            return MemoryAgentAnswerResponse.model_validate(response.json())
        except ValueError as exc:
            raise MemoryAgentUnavailable("memory agent returned an invalid answer response") from exc

    async def _post_json(
        self,
        *,
        path: str,
        payload: dict[str, Any],
        request_id: str,
        scope: str,
    ) -> httpx.Response:
        if not settings.MEMORY_AGENT_SERVICE_JWT_SECRET.get_secret_value():
            raise MemoryAgentUnavailable("memory agent service credentials are not configured")

        attempts = max(1, settings.EXTERNAL_RETRY_MAX_ATTEMPTS)
        headers = {
            "Authorization": f"Bearer {_create_service_token(scope=scope)}",
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
        }
        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.post(path, json=payload, headers=headers)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                if attempt == attempts:
                    raise MemoryAgentUnavailable("memory agent connection failed") from exc
                await _retry_delay(attempt)
                continue

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < attempts:
                await _retry_delay(attempt)
                continue
            if response.is_error:
                detail = _safe_response_detail(response)
                message = f"memory agent HTTP {response.status_code}: {detail}"
                if 400 <= response.status_code < 500:
                    raise MemoryAgentRejected(message, status_code=response.status_code)
                raise MemoryAgentUnavailable(message)
            return response

        raise MemoryAgentUnavailable("memory agent request failed")


def _create_service_token(*, scope: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "iss": SERVICE_TOKEN_ISSUER,
        "aud": SERVICE_TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + MAX_SERVICE_TOKEN_LIFETIME,
        "scope": scope,
    }
    return jwt.encode(
        payload,
        settings.MEMORY_AGENT_SERVICE_JWT_SECRET.get_secret_value(),
        algorithm=SERVICE_TOKEN_ALGORITHM,
    )


def _answer_request_payload(request: MemoryAgentAnswerRequest) -> dict[str, Any]:
    payload = request.model_dump(mode="json")
    if request.model is not None:
        payload["model"] = {
            "provider": request.model.provider,
            "base_url": request.model.base_url,
            "model_name": request.model.model_name,
            "api_key": request.model.api_key.get_secret_value(),
            "temperature": request.model.temperature,
        }
    return payload


def _safe_response_detail(response: httpx.Response) -> str:
    try:
        content = response.json()
    except ValueError:
        return "non-JSON error response"

    detail = content.get("detail", "request failed") if isinstance(content, dict) else content
    return str(_redact_private_response_data(detail))[:MAX_ERROR_DETAIL_LENGTH]


def _redact_private_response_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted>" if key.lower() in _REDACTED_RESPONSE_KEYS else _redact_private_response_data(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_private_response_data(item) for item in value]
    return value


async def _retry_delay(attempt: int) -> None:
    delay = min(
        settings.EXTERNAL_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)),
        settings.EXTERNAL_RETRY_MAX_DELAY_SECONDS,
    )
    await asyncio.sleep(delay)
