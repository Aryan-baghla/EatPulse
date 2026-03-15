from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.report_generator import generate_weekly_report
from database.queries.users import get_user
from database.queries.weekly_reports import insert_report


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool = context.bot_data["db"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        await update.message.reply_text("Please complete setup first — send /start")
        return

    await update.message.reply_text("Generating your weekly report... 📊")

    stats, report_text = await generate_weekly_report(user.telegram_id, pool)
    await insert_report(pool, user.telegram_id, stats, report_text)
    await update.message.reply_text(report_text)


def build_reports_handler() -> CommandHandler:
    return CommandHandler("report", cmd_report)
