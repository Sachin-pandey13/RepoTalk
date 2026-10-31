"""
backend/core/security.py
JWT creation, verification, and password hashing utilities.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request, Cookie
from backend.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


# ─── Token helpers ────────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise CREDENTIALS_EXCEPTION


# ─── Current user dependency ─────────────────────────────────────────────────

def get_current_user_id(
    access_token: Optional[str] = Cookie(default=None),
) -> int:
    if not access_token:
        raise CREDENTIALS_EXCEPTION
    payload = decode_token(access_token)
    user_id = payload.get("sub")
    if user_id is None:
        raise CREDENTIALS_EXCEPTION
    return int(user_id)


def get_optional_user_id(
    access_token: Optional[str] = Cookie(default=None),
) -> Optional[int]:
    """Returns None instead of raising when unauthenticated."""
    if not access_token:
        return None
    try:
        payload = decode_token(access_token)
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except Exception:
        return None
