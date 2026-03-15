from __future__ import annotations

import logging
from typing import Optional

import asyncpg
from openai import AsyncOpenAI
from telegram.ext import Application, ApplicationBuilder

from bot.handlers.calories import build_calories_handler
from bot.handlers.errors import error_handler
from bot.handlers.food_log import build_food_log_handlers
from bot.handlers.onboarding import build_onboarding_handler
from bot.handlers.reports import build_reports_handler
from bot.handlers.suggestions import build_suggestions_handler, build_swiggy_link_handler
from core.settings import settings

logger = logging.getLogger(__name__)


async def create_application(
    db_pool: asyncpg.Pool,
    openai_client: Optional[AsyncOpenAI] = None,
) -> Application:
    """Build and return the Telegram Application.

    updater=None disables the built-in polling/webhook server.
    Updates are fed externally via app.update_queue (webhook mode)
    or via run_polling() in dev mode.
    """
    builder = ApplicationBuilder().token(settings.telegram_bot_token)

    if settings.bot_mode == "webhook":
        builder = builder.updater(None)

    app = builder.build()

    # Share DB pool and OpenAI client across all handlers via bot_data
    app.bot_data["db"] = db_pool
    if openai_client:
        app.bot_data["openai"] = openai_client

    # Register handlers (order matters — more specific first)
    app.add_handler(build_onboarding_handler())
    app.add_handler(build_suggestions_handler())
    app.add_handler(build_swiggy_link_handler())
    app.add_handler(build_reports_handler())
    app.add_handler(build_calories_handler())

    for handler in build_food_log_handlers():
        app.add_handler(handler)

    app.add_error_handler(error_handler)

    logger.info("Telegram Application built (mode=%s)", settings.bot_mode)
    return app


async def run_polling(db_pool: asyncpg.Pool) -> None:
    """Run the bot in polling mode (local development only)."""
    from integrations.openai_client import init_client
    openai_client = init_client()
    app = await create_application(db_pool, openai_client)
    logger.info("Starting bot in polling mode...")
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await app.updater.idle()
        await app.stop()
