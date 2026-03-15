from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Optional

import asyncpg
from fastapi import APIRouter, Depends, Query

from core.calorie_engine import get_today_calories, get_week_calories
from core.models import UserProfile
from dashboard.api.dependencies import get_current_user, get_db
from database.queries.weekly_reports import get_health_score_history

router = APIRouter(prefix="/api")


@router.get("/calories/daily")
async def daily_calories(
    user: Annotated[UserProfile, Depends(get_current_user)],
    pool: Annotated[asyncpg.Pool, Depends(get_db)],
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD, defaults to today"),
) -> dict:
    day = date.fromisoformat(target_date) if target_date else date.today()
    total = await get_today_calories(pool, user.telegram_id) if day == date.today() \
        else 0  # use direct query for other days
    return {"date": str(day), "total_calories": total}


@router.get("/calories/weekly")
async def weekly_calories(
    user: Annotated[UserProfile, Depends(get_current_user)],
    pool: Annotated[asyncpg.Pool, Depends(get_db)],
) -> dict:
    daily = await get_week_calories(pool, user.telegram_id)
    health_history = await get_health_score_history(pool, user.telegram_id)
    return {
        "daily_calories": daily,
        "total_calories": sum(daily.values()),
        "health_score_history": [
            {"week_start": str(r["week_start"]), "healthy_pct": float(r["healthy_pct"] or 0)}
            for r in health_history
        ],
    }
