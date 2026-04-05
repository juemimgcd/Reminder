from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import bcrypt
from jose import jwt
from passlib.context import CryptContext

from conf.config import settings


# passlib 1.7.4 still probes bcrypt.__about__.__version__, which was removed in bcrypt 4.x.
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = SimpleNamespace(__version__=getattr(bcrypt, "__version__", "4"))


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


async def create_access_token(*, subject: str, expires_minutes: int | None = None, extra_claims: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    minutes = expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expire = now + timedelta(minutes=minutes)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
