from __future__ import annotations

import logging
from collections import Counter
from datetime import date, timedelta

import asyncpg

from core.models import WeeklyReportStats
from database.queries.food_logs import get_weekly_logs
from database.queries.weekly_reports import get_last_report
from integrations import openai_client

logger = logging.getLogger(__name__)

_REPORT_PROMPT = """\
You are a friendly health coach. Write a warm, motivating weekly food report for the user.

Stats for the week ({week_start} to {week_end}):
- Total calories: {total_calories} kcal
- Daily breakdown: {daily_calories}
- Healthy meals: {healthy_count} | Unhealthy meals: {unhealthy_count} ({healthy_pct:.0f}% healthy)
- Most eaten foods: {top_foods}
- Health score this week: {health_score:.1f}/10
{prev_score_line}

Write a report in 4–5 sentences using simple, encouraging language. Use emojis sparingly.
End with one actionable tip for next week.
Return only the report text, no JSON.
"""


def _compute_health_score(healthy_pct: float) -> float:
    """Map healthy meal percentage (0–100) to a 1–10 score."""
    return round(1 + (healthy_pct / 100) * 9, 1)


async def generate_weekly_report(
    user_id: int,
    pool: asyncpg.Pool,
) -> tuple[WeeklyReportStats, str]:
    """Generate the weekly report for a user. Returns (stats, report_text)."""
    today = date.today()
    # Week = last 7 days ending yesterday
    week_end = today - timedelta(days=1)
    week_start = week_end - timedelta(days=6)

    logs = await get_weekly_logs(pool, user_id, week_start)

    # Compute stats
    total_calories = sum(r["calories"] for r in logs)
    healthy_count = sum(1 for r in logs if r["is_healthy"])
    unhealthy_count = len(logs) - healthy_count
    healthy_pct = (healthy_count / len(logs) * 100) if logs else 0

    # Daily calories
    daily_calories: dict[str, int] = {}
    for r in logs:
        day_str = str(r["logged_at"].date())
        daily_calories[day_str] = daily_calories.get(day_str, 0) + r["calories"]

    # Top 3 foods
    food_counter = Counter(r["food_name"] for r in logs)
    top_foods = [f for f, _ in food_counter.most_common(3)]

    health_score = _compute_health_score(healthy_pct)

    # Previous week score
    last_report = await get_last_report(pool, user_id)
    prev_health_score = None
    if last_report and last_report["healthy_pct"] is not None:
        prev_health_score = _compute_health_score(float(last_report["healthy_pct"]))

    stats = WeeklyReportStats(
        user_id=user_id,
        week_start=str(week_start),
        week_end=str(week_end),
        total_calories=total_calories,
        daily_calories=daily_calories,
        healthy_count=healthy_count,
        unhealthy_count=unhealthy_count,
        healthy_pct=healthy_pct,
        top_foods=top_foods,
        health_score=health_score,
        prev_health_score=prev_health_score,
    )

    if not logs:
        report_text = (
            "You didn't log any meals this week. Start tracking to see your health insights! 🌱"
        )
        return stats, report_text

    prev_score_line = ""
    if prev_health_score is not None:
        delta = health_score - prev_health_score
        direction = "up" if delta >= 0 else "down"
        prev_score_line = f"- Previous week score: {prev_health_score:.1f}/10 ({direction} {abs(delta):.1f} points)"

    prompt = _REPORT_PROMPT.format(
        week_start=week_start.strftime("%b %d"),
        week_end=week_end.strftime("%b %d"),
        total_calories=total_calories,
        daily_calories=", ".join(f"{k}: {v} kcal" for k, v in sorted(daily_calories.items())),
        healthy_count=healthy_count,
        unhealthy_count=unhealthy_count,
        healthy_pct=healthy_pct,
        top_foods=", ".join(top_foods) if top_foods else "no data",
        health_score=health_score,
        prev_score_line=prev_score_line,
    )

    try:
        report_text = await openai_client.chat(
            [{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            temperature=0.6,
        )
    except Exception as e:
        logger.error("Report GPT generation failed: %s", e)
        report_text = (
            f"Week of {week_start} — {total_calories} kcal total, "
            f"{healthy_pct:.0f}% healthy meals. Health score: {health_score}/10."
        )

    return stats, report_text
