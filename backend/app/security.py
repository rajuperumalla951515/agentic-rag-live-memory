from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import User
from app.db.session import get_db_session

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def create_access_token(user_id: UUID, settings: Settings) -> tuple[str, int]:
    if settings.secret_key is None or len(settings.secret_key.get_secret_value()) < 32:
        raise RuntimeError("SECRET_KEY must contain at least 32 characters")
    expires_in = settings.access_token_expire_minutes * 60
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(seconds=expires_in)},
        settings.secret_key.get_secret_value(),
        algorithm="HS256",
    )
    return token, expires_in


async def get_current_user(
    request_settings: Settings,
    credentials: HTTPAuthorizationCredentials | None,
    session: AsyncSession,
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or request_settings.secret_key is None:
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials,
            request_settings.secret_key.get_secret_value(),
            algorithms=["HS256"],
        )
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise unauthorized from None

    user = await session.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise unauthorized
    return user


async def authenticated_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    settings: Settings = request.app.state.settings
    return await get_current_user(settings, credentials, session)
