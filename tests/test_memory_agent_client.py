import asyncio

import httpx
import jwt
import pytest
from pydantic import SecretStr

from app.mneme.clients import memory_agent_client as client_module
from app.mneme.clients.memory_agent_client import (
    MemoryAgentClient,
    MemoryAgentPermanentFailure,
    MemoryAgentRejected,
    MemoryAgentRetryable,
)
from app.mneme.conf.config import settings
from app.mneme.schemas.memory_agent import MemoryAgentAnswerRequest


def _request():
    return MemoryAgentAnswerRequest(
        request_id="request-1",
        owner_id=7,
        knowledge_base_id="kb-1",
        session_id="session-1",
        message_id="message-1",
        question="question",
        answer_mode="kb_qa",
    )


def _run_client(handler, operation):
    async def run():
        transport = httpx.MockTransport(handler)
        async with MemoryAgentClient() as client:
            await client._client.aclose()
            client._client = httpx.AsyncClient(transport=transport, base_url="http://agent")
            return await operation(client)

    return asyncio.run(run())


def test_client_builds_scoped_service_token_and_parses_answer(monkeypatch):
    monkeypatch.setattr(settings, "MEMORY_AGENT_SERVICE_JWT_SECRET", SecretStr("secret"))
    seen = {}

    def handler(request):
        seen["authorization"] = request.headers["authorization"]
        return httpx.Response(
            200,
            json={"answer": "ok", "mode": "kb_qa", "route": "kb_qa", "confidence": 0.9, "run_id": "run-1"},
        )

    response = _run_client(handler, lambda client: client.create_answer(_request()))

    claims = jwt.decode(seen["authorization"].split()[1], "secret", algorithms=["HS256"], options={"verify_aud": False})
    assert claims["scope"] == "answers:write"
    assert claims["owner_id"] == 7
    assert claims["knowledge_base_id"] == "kb-1"
    assert response.run_id == "run-1"


def test_client_retries_503_for_event_delivery(monkeypatch):
    monkeypatch.setattr(settings, "MEMORY_AGENT_SERVICE_JWT_SECRET", SecretStr("secret"))
    monkeypatch.setattr(client_module, "_retry_delay", lambda _attempt: asyncio.sleep(0))
    calls = 0

    def handler(_request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"code": "AGENT_UNAVAILABLE"})
        return httpx.Response(200, json={"event_id": "event-1", "accepted": True, "duplicate": False})

    event = {
        "event_id": "event-1",
        "event_type": "user.memory_requested",
        "schema_version": "1",
        "occurred_at": "2026-07-15T00:00:00Z",
        "owner_id": 7,
        "payload": {},
    }
    fake_event = type(
        "Event",
        (),
        {"event_id": "event-1", "model_dump": lambda self, **_: event},
    )()
    receipt = _run_client(handler, lambda client: client.submit_event(fake_event))

    assert calls == 2
    assert receipt.accepted is True


@pytest.mark.parametrize("status,expected", [(422, MemoryAgentRejected), (503, MemoryAgentRetryable)])
def test_client_maps_http_errors_without_fabricating_success(monkeypatch, status, expected):
    monkeypatch.setattr(settings, "MEMORY_AGENT_SERVICE_JWT_SECRET", SecretStr("secret"))

    def handler(_request):
        return httpx.Response(status, json={"code": "AGENT_VALIDATION_ERROR"})

    with pytest.raises(expected):
        _run_client(handler, lambda client: client.create_answer(_request()))


def test_client_rejects_malformed_agent_response(monkeypatch):
    monkeypatch.setattr(settings, "MEMORY_AGENT_SERVICE_JWT_SECRET", SecretStr("secret"))

    with pytest.raises(MemoryAgentPermanentFailure):
        _run_client(
            lambda _request: httpx.Response(200, content=b"not-json"),
            lambda client: client.create_answer(_request()),
        )
