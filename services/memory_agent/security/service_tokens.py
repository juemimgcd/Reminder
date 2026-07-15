from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pydantic import SecretStr

SERVICE_TOKEN_ISSUER = "mneme-backend"
EVENTS_WRITE_SCOPE = "events:write"
ANSWERS_WRITE_SCOPE = "answers:write"
RUNS_READ_SCOPE = "runs:read"
MEMORIES_READ_SCOPE = "memories:read"
MEMORIES_WRITE_SCOPE = "memories:write"
SERVICE_TOKEN_ALGORITHM = "HS256"


def create_service_token(
    secret: SecretStr | str,
    *,
    audience: str = "memory-agent",
    expires_in: timedelta = timedelta(minutes=5),
) -> str:
    now = datetime.now(UTC)
    payload = {
        "iss": SERVICE_TOKEN_ISSUER,
        "aud": audience,
        "iat": now,
        "exp": now + expires_in,
        "scope": EVENTS_WRITE_SCOPE,
    }
    return jwt.encode(payload, _secret_value(secret), algorithm=SERVICE_TOKEN_ALGORITHM)


def decode_service_token(
    token: str,
    secret: SecretStr | str,
    *,
    audience: str = "memory-agent",
) -> dict[str, Any]:
    return jwt.decode(
        token,
        _secret_value(secret),
        algorithms=[SERVICE_TOKEN_ALGORITHM],
        audience=audience,
        issuer=SERVICE_TOKEN_ISSUER,
        options={"require": ["iss", "aud", "iat", "exp", "scope"]},
    )


def _secret_value(secret: SecretStr | str) -> str:
    if isinstance(secret, SecretStr):
        return secret.get_secret_value()
    return secret
