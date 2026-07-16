import asyncio
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.mneme.memoria.server.api.dependencies import require_event_service_token
from app.mneme.memoria.server.app import create_memory_agent_app
from app.mneme.memoria.server.config import settings
from app.mneme.memoria.server.security.service_tokens import SERVICE_TOKEN_ISSUER
from app.mneme.utils.security import create_access_token

SECRET = settings.SERVICE_JWT_SECRET.get_secret_value()


def token(**overrides):
    now = datetime.now(UTC)
    claims = {
        "iss": SERVICE_TOKEN_ISSUER,
        "aud": settings.SERVICE_JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "scope": "events:write",
    }
    claims.update(overrides)
    return jwt.encode(claims, SECRET, algorithm="HS256")


def authorize(value):
    credentials = None if value is None else HTTPAuthorizationCredentials(scheme="Bearer", credentials=value)
    return asyncio.run(require_event_service_token(credentials))


def test_valid_service_token_is_authorized():
    assert authorize(token())["scope"] == "events:write"


@pytest.mark.parametrize(
    ("value", "expected_status"),
    [
        (None, 401),
        (token(exp=datetime.now(UTC) - timedelta(seconds=1)), 401),
        (token(iss="mneme-user-api"), 401),
        (token(aud="mneme-user"), 401),
        (token(scope="answers:write"), 403),
    ],
)
def test_invalid_or_user_tokens_are_rejected(value, expected_status):
    with pytest.raises(HTTPException) as raised:
        authorize(value)

    assert raised.value.status_code == expected_status


def test_mneme_user_access_token_cannot_access_internal_events():
    user_token = asyncio.run(create_access_token(subject="7"))

    with pytest.raises(HTTPException) as raised:
        authorize(user_token)

    assert raised.value.status_code == 401


def test_internal_events_route_rejects_missing_and_mneme_user_tokens():
    app = create_memory_agent_app()
    payload = {
        "event_id": "route-auth-event",
        "event_type": "conversation.completed",
        "schema_version": "1",
        "occurred_at": "2026-07-15T00:00:00Z",
        "owner_id": 7,
        "knowledge_base_id": None,
        "payload": {"session_id": "session-1"},
    }
    user_token = asyncio.run(create_access_token(subject="7"))

    with TestClient(app) as client:
        missing = client.post("/internal/v1/events", json=payload)
        user = client.post(
            "/internal/v1/events",
            json=payload,
            headers={"Authorization": f"Bearer {user_token}"},
        )

    assert missing.status_code == 401
    assert user.status_code == 401
