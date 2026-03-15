from __future__ import annotations

import logging

import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from core.report_generator import generate_weekly_report
from database.queries.users import get_all_active_user_ids
from database.queries.weekly_reports import insert_report

logger = logging.getLogger(__name__)


async def send_weekly_reports(bot: Bot, pool: asyncpg.Pool) -> None:
    """Generate and send weekly reports to all active users.

    Called every Sunday at 20:00 IST (14:30 UTC).
    """
    user_ids = await get_all_active_user_ids(pool)
    logger.info("Sending weekly reports to %d users", len(user_ids))

    for user_id in user_ids:
        try:
            stats, report_text = await generate_weekly_report(user_id, pool)
            await insert_report(pool, user_id, stats, report_text)
            await bot.send_message(chat_id=user_id, text=report_text)
            logger.debug("Sent weekly report to user %d", user_id)
        except Exception as e:
            logger.error("Failed to send weekly report to user %d: %s", user_id, e)


def register_jobs(scheduler: AsyncIOScheduler, bot: Bot, pool: asyncpg.Pool) -> None:
    """Register all scheduled jobs onto the given scheduler."""
    scheduler.add_job(
        send_weekly_reports,
        trigger=CronTrigger(
            day_of_week="sun",
            hour=14,
            minute=30,
            timezone="UTC",  # 14:30 UTC = 20:00 IST
        ),
        args=[bot, pool],
        id="weekly_reports",
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1h late start if server was down
    )
    logger.info("Scheduled weekly report job (Sunday 20:00 IST)")
