from __future__ import annotations

from datetime import datetime
from typing import Optional

import asyncpg

from core.models import UserProfile


async def upsert_user(pool: asyncpg.Pool, profile: UserProfile) -> None:
    await pool.execute(
        """
        INSERT INTO users (telegram_id, name, city, pincode, dietary_preference, timezone)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (telegram_id) DO UPDATE SET
            name               = EXCLUDED.name,
            city               = EXCLUDED.city,
            pincode            = EXCLUDED.pincode,
            dietary_preference = EXCLUDED.dietary_preference,
            timezone           = EXCLUDED.timezone
        """,
        profile.telegram_id,
        profile.name,
        profile.city,
        profile.pincode,
        profile.dietary_preference,
        profile.timezone,
    )


async def get_user(pool: asyncpg.Pool, telegram_id: int) -> Optional[UserProfile]:
    row = await pool.fetchrow(
        "SELECT * FROM users WHERE telegram_id = $1",
        telegram_id,
    )
    if row is None:
        return None
    return UserProfile(
        telegram_id=row["telegram_id"],
        name=row["name"],
        city=row["city"],
        pincode=row["pincode"],
        dietary_preference=row["dietary_preference"],
        timezone=row["timezone"],
        swiggy_phone=row["swiggy_phone"],
        swiggy_session_token=row["swiggy_session_token"],
    )


async def update_swiggy_token(
    pool: asyncpg.Pool,
    telegram_id: int,
    phone: str,
    token: str,
    expires_at: datetime,
) -> None:
    await pool.execute(
        """
        UPDATE users SET
            swiggy_phone            = $2,
            swiggy_session_token    = $3,
            swiggy_token_expires_at = $4
        WHERE telegram_id = $1
        """,
        telegram_id,
        phone,
        token,
        expires_at,
    )


async def clear_swiggy_token(pool: asyncpg.Pool, telegram_id: int) -> None:
    await pool.execute(
        """
        UPDATE users SET
            swiggy_session_token    = NULL,
            swiggy_token_expires_at = NULL
        WHERE telegram_id = $1
        """,
        telegram_id,
    )


async def get_all_active_user_ids(pool: asyncpg.Pool) -> list[int]:
    """Return telegram_ids of all users who have logged food in the last 8 days."""
    rows = await pool.fetch(
        """
        SELECT DISTINCT user_id
        FROM food_logs
        WHERE logged_at >= NOW() - INTERVAL '8 days'
        """
    )
    return [r["user_id"] for r in rows]
