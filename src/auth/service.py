import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.config import auth_settings
from src.auth.exceptions import InvalidCredentials, UserAlreadyExists
from src.auth.models import User
from src.auth.schemas import UserCreate


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(32)
    key = hashlib.scrypt(
        password.encode("utf-8"), salt=salt.encode("utf-8"), n=2**14, r=8, p=1, dklen=32
    )
    return f"scrypt${salt}${key.hex()}"


def _verify_password(password: str, hashed: str) -> bool:
    try:
        _, salt, key_hex = hashed.split("$")
        key = hashlib.scrypt(
            password.encode("utf-8"), salt=salt.encode("utf-8"), n=2**14, r=8, p=1, dklen=32
        )
        return secrets.compare_digest(key, bytes.fromhex(key_hex))
    except Exception:
        return False


def create_access_token(user_id: int) -> str:
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) + timedelta(minutes=auth_settings.JWT_EXP_MINUTES),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, auth_settings.JWT_SECRET, algorithm=auth_settings.JWT_ALG)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, auth_settings.JWT_SECRET, algorithms=[auth_settings.JWT_ALG])
    except jwt.InvalidTokenError as exc:
        raise InvalidCredentials() from exc


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    existing = await get_user_by_username(db, data.username)
    if existing:
        raise UserAlreadyExists()
    user = User(
        username=data.username,
        email=str(data.email),
        hashed_password=_hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User:
    user = await get_user_by_username(db, username)
    if not user or not _verify_password(password, user.hashed_password):
        raise InvalidCredentials()
    if not user.is_active:
        raise InvalidCredentials()
    return user
