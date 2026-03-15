from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Optional

import asyncpg
from fastapi import APIRouter, Depends, Query

from core.models import UserProfile
from dashboard.api.dependencies import get_current_user, get_db
from database.queries.food_logs import get_weekly_logs

router = APIRouter(prefix="/api")


@router.get("/logs")
async def get_logs(
    user: Annotated[UserProfile, Depends(get_current_user)],
    pool: Annotated[asyncpg.Pool, Depends(get_db)],
    week_start: Optional[str] = Query(None, description="YYYY-MM-DD, defaults to current week Monday"),
) -> dict:
    """Return food logs for a given week, structured for the timetable view."""
    if week_start:
        ws = date.fromisoformat(week_start)
    else:
        today = date.today()
        ws = today - timedelta(days=today.weekday())  # Monday

    logs = await get_weekly_logs(pool, user.telegram_id, ws)

    # Structure: { "2026-03-15": { "breakfast": [...], "lunch": [...], ... } }
    timetable: dict[str, dict[str, list]] = {}
    for log in logs:
        day_str = str(log["logged_at"].date())
        if day_str not in timetable:
            timetable[day_str] = {
                "breakfast": [],
                "lunch": [],
                "snacks": [],
                "dinner": [],
            }
        timetable[day_str][log["meal_type"]].append({
            "id": log["id"],
            "food_name": log["food_name"],
            "calories": log["calories"],
            "is_healthy": log["is_healthy"],
            "meal_type": log["meal_type"],
            "logged_at": log["logged_at"].isoformat(),
        })

    # Fill in missing days in the week
    for i in range(7):
        day = ws + timedelta(days=i)
        day_str = str(day)
        if day_str not in timetable:
            timetable[day_str] = {
                "breakfast": [],
                "lunch": [],
                "snacks": [],
                "dinner": [],
            }

    return {
        "week_start": str(ws),
        "week_end": str(ws + timedelta(days=6)),
        "timetable": timetable,
    }
