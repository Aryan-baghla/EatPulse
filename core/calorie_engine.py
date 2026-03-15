from __future__ import annotations

from datetime import date, timedelta

import asyncpg

from database.queries.food_logs import get_daily_calorie_total, get_daily_logs


async def get_today_calories(pool: asyncpg.Pool, user_id: int) -> int:
    return await get_daily_calorie_total(pool, user_id, date.today())


async def get_week_calories(pool: asyncpg.Pool, user_id: int) -> dict[str, int]:
    """Return a dict of {date_str: calories} for the last 7 days."""
    today = date.today()
    result: dict[str, int] = {}
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        total = await get_daily_calorie_total(pool, user_id, day)
        result[str(day)] = total
    return result
