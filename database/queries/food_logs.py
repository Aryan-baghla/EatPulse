from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import asyncpg

from core.models import FoodEntry


async def insert_food_log(
    pool: asyncpg.Pool,
    entry: FoodEntry,
    user_id: int,
    logged_at: datetime,
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO food_logs
            (user_id, food_name, calories, is_healthy, meal_type, input_type, raw_input, logged_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        user_id,
        entry.food_name,
        entry.calories,
        entry.is_healthy,
        entry.meal_type,
        entry.input_type,
        entry.raw_input,
        logged_at,
    )
    return row["id"]


async def get_daily_logs(
    pool: asyncpg.Pool,
    user_id: int,
    day: date,
) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT id, food_name, calories, is_healthy, meal_type, input_type, logged_at
        FROM food_logs
        WHERE user_id = $1
          AND logged_at >= $2::date
          AND logged_at < ($2::date + INTERVAL '1 day')
        ORDER BY logged_at ASC
        """,
        user_id,
        day,
    )
    return [dict(r) for r in rows]


async def get_weekly_logs(
    pool: asyncpg.Pool,
    user_id: int,
    week_start: date,
) -> list[dict]:
    week_end = date(week_start.year, week_start.month, week_start.day)
    rows = await pool.fetch(
        """
        SELECT id, food_name, calories, is_healthy, meal_type, input_type, logged_at
        FROM food_logs
        WHERE user_id = $1
          AND logged_at >= $2::date
          AND logged_at < ($2::date + INTERVAL '7 days')
        ORDER BY logged_at ASC
        """,
        user_id,
        week_start,
    )
    return [dict(r) for r in rows]


async def get_daily_calorie_total(
    pool: asyncpg.Pool,
    user_id: int,
    day: date,
) -> int:
    row = await pool.fetchrow(
        """
        SELECT COALESCE(SUM(calories), 0) AS total
        FROM food_logs
        WHERE user_id = $1
          AND logged_at >= $2::date
          AND logged_at < ($2::date + INTERVAL '1 day')
        """,
        user_id,
        day,
    )
    return row["total"]


async def get_history_for_suggestion(
    pool: asyncpg.Pool,
    user_id: int,
    want_healthy: Optional[bool],
    want_to_cook: Optional[bool],
    limit: int = 30,
) -> list[str]:
    """Return distinct food names matching the user's suggestion preferences."""
    query = """
        SELECT DISTINCT food_name
        FROM food_logs
        WHERE user_id = $1
    """
    params: list = [user_id]

    if want_healthy is not None:
        params.append(want_healthy)
        query += f" AND is_healthy = ${len(params)}"

    query += f" ORDER BY MAX(logged_at) DESC LIMIT ${len(params) + 1}"
    params.append(limit)

    # Need aggregate for ORDER BY — rewrite as subquery
    query = f"""
        SELECT food_name FROM (
            SELECT food_name, MAX(logged_at) AS last_eaten
            FROM food_logs
            WHERE user_id = $1
            {'AND is_healthy = $2' if want_healthy is not None else ''}
            GROUP BY food_name
            ORDER BY last_eaten DESC
            LIMIT ${len(params)}
        ) t
    """
    rows = await pool.fetch(query, *params)
    return [r["food_name"] for r in rows]


async def count_history_entries(
    pool: asyncpg.Pool,
    user_id: int,
    want_healthy: Optional[bool],
) -> int:
    if want_healthy is not None:
        row = await pool.fetchrow(
            "SELECT COUNT(*) AS cnt FROM food_logs WHERE user_id = $1 AND is_healthy = $2",
            user_id,
            want_healthy,
        )
    else:
        row = await pool.fetchrow(
            "SELECT COUNT(*) AS cnt FROM food_logs WHERE user_id = $1",
            user_id,
        )
    return row["cnt"]
