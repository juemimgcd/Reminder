from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.mneme.memoria.server.config import settings
from app.mneme.memoria.server.security.service_tokens import EVENTS_WRITE_SCOPE, decode_service_token

service_bearer = HTTPBearer(auto_error=False)


async def require_event_service_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(service_bearer)],
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="service token required")

    try:
        claims = decode_service_token(
            credentials.credentials,
            settings.SERVICE_JWT_SECRET,
            audience=settings.SERVICE_JWT_AUDIENCE,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid service token") from exc

    if claims["scope"] != EVENTS_WRITE_SCOPE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient service scope")
    return claims


def require_service_scope(required_scope: str):
    async def dependency(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(service_bearer)],
    ) -> dict[str, Any]:
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="service token required")
        try:
            claims = decode_service_token(
                credentials.credentials,
                settings.SERVICE_JWT_SECRET,
                audience=settings.SERVICE_JWT_AUDIENCE,
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid service token") from exc
        scopes = claims.get("scope")
        if isinstance(scopes, str):
            granted = set(scopes.split())
        elif isinstance(scopes, list) and all(isinstance(scope, str) for scope in scopes):
            granted = set(scopes)
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid service scope")
        if required_scope not in granted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient service scope")
        if "owner_id" not in claims or "knowledge_base_id" not in claims:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="service scope is incomplete")
        return claims

    return dependency


def require_claimed_scope(claims: dict[str, Any], *, owner_id: int, knowledge_base_id: str | None) -> None:
    claimed_owner = claims.get("owner_id")
    claimed_kb = claims.get("knowledge_base_id")
    valid_owner = isinstance(claimed_owner, int) and not isinstance(claimed_owner, bool) and claimed_owner > 0
    valid_kb = claimed_kb is None or isinstance(claimed_kb, str)
    if not valid_owner or not valid_kb or claimed_owner != owner_id or claimed_kb != knowledge_base_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="request scope does not match service token")
