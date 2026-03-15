from __future__ import annotations

from datetime import date
from typing import Optional

import asyncpg

from core.models import WeeklyReportStats


async def insert_report(
    pool: asyncpg.Pool,
    user_id: int,
    stats: WeeklyReportStats,
    report_text: str,
) -> None:
    await pool.execute(
        """
        INSERT INTO weekly_reports
            (user_id, week_start, report_text, total_calories, healthy_pct)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (user_id, week_start) DO UPDATE SET
            report_text    = EXCLUDED.report_text,
            total_calories = EXCLUDED.total_calories,
            healthy_pct    = EXCLUDED.healthy_pct
        """,
        user_id,
        date.fromisoformat(stats.week_start),
        report_text,
        stats.total_calories,
        stats.healthy_pct,
    )


async def get_last_report(
    pool: asyncpg.Pool,
    user_id: int,
) -> Optional[dict]:
    row = await pool.fetchrow(
        """
        SELECT week_start, total_calories, healthy_pct, report_text
        FROM weekly_reports
        WHERE user_id = $1
        ORDER BY week_start DESC
        LIMIT 1
        """,
        user_id,
    )
    return dict(row) if row else None


async def get_health_score_history(
    pool: asyncpg.Pool,
    user_id: int,
    limit: int = 8,
) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT week_start, healthy_pct
        FROM weekly_reports
        WHERE user_id = $1
        ORDER BY week_start DESC
        LIMIT $2
        """,
        user_id,
        limit,
    )
    return [dict(r) for r in rows]
