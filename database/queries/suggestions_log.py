from __future__ import annotations

import asyncpg

from core.models import SuggestionPreferences


async def insert_suggestion(
    pool: asyncpg.Pool,
    user_id: int,
    suggestion_text: str,
    preferences: SuggestionPreferences,
    source: str,
) -> None:
    await pool.execute(
        """
        INSERT INTO suggestions_log
            (user_id, suggestion_text, preference_healthy, preference_cook, source)
        VALUES ($1, $2, $3, $4, $5)
        """,
        user_id,
        suggestion_text,
        preferences.want_healthy,
        preferences.want_to_cook,
        source,
    )
