from __future__ import annotations

from datetime import date

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.calorie_engine import get_today_calories, get_week_calories
from database.queries.users import get_user


async def cmd_calories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool = context.bot_data["db"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        await update.message.reply_text("Please complete setup first — send /start")
        return

    today_total = await get_today_calories(pool, user.telegram_id)
    week_calories = await get_week_calories(pool, user.telegram_id)

    week_lines = []
    for day_str, cals in sorted(week_calories.items()):
        day = date.fromisoformat(day_str)
        label = "Today" if day == date.today() else day.strftime("%a %b %d")
        week_lines.append(f"  {label}: {cals} kcal")

    text = (
        f"🔥 *Today's calories:* {today_total} kcal\n\n"
        f"📅 *This week:*\n" + "\n".join(week_lines)
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def build_calories_handler() -> CommandHandler:
    return CommandHandler("calories", cmd_calories)
