from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response
from telegram import Update

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/bot/webhook")
async def telegram_webhook(request: Request) -> dict:
    """Receive Telegram updates and feed them to the bot Application."""
    data = await request.json()
    tg_app = request.app.state.tg_app

    update = Update.de_json(data, tg_app.bot)
    await tg_app.update_queue.put(update)
    return {"ok": True}
