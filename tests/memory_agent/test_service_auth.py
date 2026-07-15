import asyncio
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.mneme.utils.security import create_access_token
from services.memory_agent.api.dependencies import require_event_service_token
from services.memory_agent.config import settings
from services.memory_agent.security.service_tokens import SERVICE_TOKEN_ISSUER

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
