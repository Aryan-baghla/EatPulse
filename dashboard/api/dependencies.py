from __future__ import annotations

from typing import Annotated

import asyncpg
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.models import UserProfile
from dashboard.api.auth import decode_access_token
from database.queries.users import get_user

security = HTTPBearer()


async def get_db(request: Request) -> asyncpg.Pool:
    return request.app.state.db


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    pool: Annotated[asyncpg.Pool, Depends(get_db)],
) -> UserProfile:
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    telegram_id = int(payload["sub"])
    user = await get_user(pool, telegram_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found — please complete Telegram bot setup",
        )
    return user
