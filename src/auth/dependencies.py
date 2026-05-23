from typing import Annotated

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import service as auth_service
from src.auth.exceptions import InvalidCredentials
from src.auth.models import User
from src.database import get_db
from src.exceptions import RedirectToLogin


async def require_auth(
    request: Request,
    token: Annotated[str | None, Cookie(alias="access_token")] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> User:
    """Dependency for HTML routes — redirects to login on failure."""
    if not token:
        raise RedirectToLogin(next_url=str(request.url.path))
    try:
        payload = auth_service.decode_access_token(token)
        user_id = int(payload["sub"])
        user = await auth_service.get_user_by_id(db, user_id)
        if not user or not user.is_active:
            raise RedirectToLogin(next_url=str(request.url.path))
        return user
    except (InvalidCredentials, KeyError, ValueError):
        raise RedirectToLogin(next_url=str(request.url.path)) from None


CurrentUser = Annotated[User, Depends(require_auth)]
