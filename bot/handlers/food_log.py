from __future__ import annotations

import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from core.parser import parse_food
from database.queries.food_logs import insert_food_log
from database.queries.users import get_user

logger = logging.getLogger(__name__)


def _health_emoji(is_healthy: bool) -> str:
    return "✅" if is_healthy else "⚠️"


def _meal_emoji(meal_type: str) -> str:
    return {"breakfast": "🌅", "lunch": "☀️", "snacks": "🍎", "dinner": "🌙"}.get(meal_type, "🍽️")


async def handle_food_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool = context.bot_data["db"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        await update.message.reply_text(
            "Please complete setup first — send /start"
        )
        return

    await update.message.reply_text("Analysing your meal... ⏳")

    timestamp = update.message.date or datetime.now(timezone.utc)
    entry = await parse_food(
        input_text=update.message.text,
        image_bytes=None,
        timestamp=timestamp,
        user_timezone=user.timezone,
    )

    await insert_food_log(pool, entry, user.telegram_id, timestamp)

    health_icon = _health_emoji(entry.is_healthy)
    meal_icon = _meal_emoji(entry.meal_type)
    health_label = "Healthy" if entry.is_healthy else "Unhealthy"

    await update.message.reply_text(
        f"{meal_icon} *{entry.meal_type.title()}* logged\n"
        f"🍽️ {entry.food_name}\n"
        f"🔥 ~{entry.calories} kcal\n"
        f"{health_icon} {health_label}",
        parse_mode="Markdown",
    )


async def handle_food_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool = context.bot_data["db"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        await update.message.reply_text("Please complete setup first — send /start")
        return

    await update.message.reply_text("Analysing your meal photo... 📷⏳")

    # Download the largest photo size
    photo = update.message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    image_bytes = await photo_file.download_as_bytearray()

    timestamp = update.message.date or datetime.now(timezone.utc)
    entry = await parse_food(
        input_text=None,
        image_bytes=bytes(image_bytes),
        timestamp=timestamp,
        user_timezone=user.timezone,
    )

    await insert_food_log(pool, entry, user.telegram_id, timestamp)

    health_icon = _health_emoji(entry.is_healthy)
    meal_icon = _meal_emoji(entry.meal_type)
    health_label = "Healthy" if entry.is_healthy else "Unhealthy"

    await update.message.reply_text(
        f"{meal_icon} *{entry.meal_type.title()}* logged\n"
        f"🍽️ {entry.food_name}\n"
        f"🔥 ~{entry.calories} kcal\n"
        f"{health_icon} {health_label}",
        parse_mode="Markdown",
    )


def build_food_log_handlers() -> list:
    return [
        MessageHandler(filters.PHOTO, handle_food_photo),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_food_text),
    ]
