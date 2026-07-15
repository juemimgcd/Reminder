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
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class MemoryAgentUnavailable(BusinessException):
    def __init__(self, message: str, *, status_code: int = 503, agent_code: str | None = None):
        super().__init__(message=message, code=5032, status_code=status_code)
        self.agent_code = agent_code

    def __str__(self) -> str:
        return self.message


class MemoryAgentRetryable(MemoryAgentUnavailable):
    pass


class MemoryAgentPermanentFailure(MemoryAgentUnavailable):
    pass


class MemoryAgentRejected(MemoryAgentPermanentFailure):
    def __init__(self, message: str, *, status_code: int):
        BusinessException.__init__(self, message=message, code=4025, status_code=status_code)


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
            retry_transient=True,
        )
        try:
            return EventReceipt.model_validate(response.json())
        except ValueError as exc:
            raise MemoryAgentPermanentFailure("memory agent returned an invalid event receipt") from exc

    async def create_answer(self, request: MemoryAgentAnswerRequest) -> MemoryAgentAnswerResponse:
        response = await self._post_json(
            path="/v1/answers",
            payload=_answer_request_payload(request),
            request_id=request.request_id,
            scope="answers:write",
            owner_id=request.owner_id,
            knowledge_base_id=request.knowledge_base_id,
            retry_transient=False,
        )
        try:
            return MemoryAgentAnswerResponse.model_validate(response.json())
        except ValueError as exc:
            raise MemoryAgentPermanentFailure("memory agent returned an invalid answer response") from exc

    async def _post_json(
        self,
        *,
        path: str,
        payload: dict[str, Any],
        request_id: str,
        scope: str,
        owner_id: int | None = None,
        knowledge_base_id: str | None = None,
        retry_transient: bool,
    ) -> httpx.Response:
        if not settings.MEMORY_AGENT_SERVICE_JWT_SECRET.get_secret_value():
            raise MemoryAgentPermanentFailure("memory agent service credentials are not configured")

        attempts = max(1, settings.EXTERNAL_RETRY_MAX_ATTEMPTS)
        try:
            service_token = _create_service_token(
                scope=scope,
                owner_id=owner_id,
                knowledge_base_id=knowledge_base_id,
            )
        except Exception as exc:
            raise MemoryAgentPermanentFailure("memory agent service token creation failed") from exc
        headers = {
            "Authorization": f"Bearer {service_token}",
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
        }
        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.post(path, json=payload, headers=headers)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
                if not retry_transient or attempt == attempts:
                    raise MemoryAgentRetryable("memory agent connection failed") from exc
                await _retry_delay(attempt)
                continue
            except httpx.HTTPError as exc:
                raise MemoryAgentPermanentFailure("memory agent transport failed") from exc
            except Exception as exc:
                raise MemoryAgentPermanentFailure("memory agent request failed") from exc

            if retry_transient and response.status_code in RETRYABLE_STATUS_CODES and attempt < attempts:
                await _retry_delay(attempt)
                continue
            if response.is_error:
                agent_code = _agent_error_code(response)
                message = f"memory agent HTTP {response.status_code}: {_http_error_reason(response.status_code)}"
                if response.status_code in RETRYABLE_STATUS_CODES:
                    raise MemoryAgentRetryable(message, agent_code=agent_code)
                if 400 <= response.status_code < 500:
                    raise MemoryAgentRejected(message, status_code=response.status_code)
                raise MemoryAgentPermanentFailure(message, agent_code=agent_code)
            return response

        raise MemoryAgentPermanentFailure("memory agent request failed")


def _create_service_token(
    *, scope: str, owner_id: int | None = None, knowledge_base_id: str | None = None
) -> str:
    now = datetime.now(UTC)
    payload = {
        "iss": SERVICE_TOKEN_ISSUER,
        "aud": SERVICE_TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + MAX_SERVICE_TOKEN_LIFETIME,
        "scope": scope,
    }
    if scope != "events:write":
        payload["owner_id"] = owner_id
        payload["knowledge_base_id"] = knowledge_base_id
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


def _http_error_reason(status_code: int) -> str:
    if 400 <= status_code < 500:
        return "request rejected"
    if status_code in RETRYABLE_STATUS_CODES:
        return "service temporarily unavailable"
    return "service request failed"


def _agent_error_code(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    code = payload.get("code") if isinstance(payload, dict) else None
    return code if isinstance(code, str) and len(code) <= 64 else None


async def _retry_delay(attempt: int) -> None:
    delay = min(
        settings.EXTERNAL_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)),
        settings.EXTERNAL_RETRY_MAX_DELAY_SECONDS,
    )
    await asyncio.sleep(delay)
