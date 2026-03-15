from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import asyncpg
import pytz

from core.classifier import meal_type_from_hour
from core.models import Suggestion, SuggestedItem, SuggestionPreferences, UserProfile
from database.queries.food_logs import count_history_entries, get_history_for_suggestion
from integrations import openai_client
from integrations.swiggy_mcp import swiggy_client
from integrations.zomato import build_deep_link

logger = logging.getLogger(__name__)

_HISTORY_THRESHOLD = 20  # min entries before showing "from history" suggestions

_SUGGEST_SYSTEM_PROMPT = """\
You are a food suggestion assistant for Indian users.
Suggest {count} {meal_type} options that are {health_pref} to {action}.
The user's dietary preference is: {diet}.
Return a JSON object with a "suggestions" array. Each item must have:
  "name": concise food name,
  "description": one-line description (max 15 words),
  "estimated_calories": integer calories for one serving.

Return only valid JSON.
"""


async def get_suggestion(
    profile: UserProfile,
    preferences: SuggestionPreferences,
    pool: asyncpg.Pool,
    timestamp: Optional[datetime] = None,
) -> Suggestion:
    if timestamp is None:
        timestamp = datetime.now(pytz.timezone(profile.timezone))

    try:
        local_dt = timestamp.astimezone(pytz.timezone(profile.timezone))
    except Exception:
        local_dt = timestamp
    meal_type = meal_type_from_hour(local_dt.hour)

    health_pref = "healthy" if preferences.want_healthy else "indulgent/comfort"
    action = "cook at home" if preferences.want_to_cook else "order for delivery"

    if preferences.from_history:
        items = await _from_history(pool, profile.telegram_id, preferences)
    else:
        items = await _from_gpt(
            meal_type=meal_type,
            health_pref=health_pref,
            action=action,
            diet=profile.dietary_preference,
        )

    swiggy_results = []
    zomato_link = None

    if not preferences.want_to_cook and items:
        query = items[0].name if items else meal_type
        if profile.swiggy_session_token:
            swiggy_results = await swiggy_client.search(
                query=query,
                pincode=profile.pincode,
                session_token=profile.swiggy_session_token,
            )
        if not swiggy_results:
            zomato_link = build_deep_link(query, profile.city)

    return Suggestion(items=items, swiggy_results=swiggy_results, zomato_deep_link=zomato_link)


async def _from_history(
    pool: asyncpg.Pool,
    user_id: int,
    preferences: SuggestionPreferences,
) -> list[SuggestedItem]:
    count = await count_history_entries(pool, user_id, preferences.want_healthy)
    if count < _HISTORY_THRESHOLD:
        logger.info("User %d has only %d matching history entries — falling back to GPT", user_id, count)
        # Signal to caller to fall back; return empty so Suggestion shows GPT path
        return []

    food_names = await get_history_for_suggestion(
        pool, user_id, preferences.want_healthy, preferences.want_to_cook
    )
    return [
        SuggestedItem(
            name=name,
            description="From your history",
            estimated_calories=0,
            source="history",
        )
        for name in food_names[:5]
    ]


async def _from_gpt(
    meal_type: str,
    health_pref: str,
    action: str,
    diet: str,
    count: int = 4,
) -> list[SuggestedItem]:
    prompt = _SUGGEST_SYSTEM_PROMPT.format(
        count=count,
        meal_type=meal_type,
        health_pref=health_pref,
        action=action,
        diet=diet,
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Suggest {count} {meal_type} options for me."},
    ]
    try:
        result = await openai_client.chat_json(messages, model="gemini-1.5-flash")
        suggestions = result.get("suggestions", [])
        return [
            SuggestedItem(
                name=s["name"],
                description=s.get("description", ""),
                estimated_calories=int(s.get("estimated_calories", 0)),
                source="gpt",
            )
            for s in suggestions
        ]
    except Exception as e:
        logger.error("GPT suggestion failed: %s", e)
        return []
