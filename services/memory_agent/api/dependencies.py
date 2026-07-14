from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.memory_agent.config import settings
from services.memory_agent.security.service_tokens import EVENTS_WRITE_SCOPE, decode_service_token

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
