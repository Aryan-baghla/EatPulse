from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.keyboards import cancel_keyboard, diet_keyboard, timezone_keyboard
from bot.states import (
    ONBOARDING_CITY,
    ONBOARDING_DIET,
    ONBOARDING_NAME,
    ONBOARDING_PINCODE,
    ONBOARDING_TIMEZONE,
)
from core.models import UserProfile
from database.queries.users import get_user, upsert_user

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    pool = context.bot_data["db"]
    user = await get_user(pool, update.effective_user.id)

    if user:
        await update.message.reply_text(
            f"Welcome back, {user.name}! 👋\n\n"
            "Send me what you ate, or use /suggest to get food ideas.\n"
            "Use /calories for today's count, /report for your weekly summary."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "👋 Welcome to *EatPulse* — your personal food tracker!\n\n"
        "I'll help you track meals, suggest what to eat, and send weekly health reports.\n\n"
        "Let's set you up quickly. What's your name?",
        parse_mode="Markdown",
    )
    return ONBOARDING_NAME


async def received_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    name = update.message.text.strip()
    if not name or len(name) > 100:
        await update.message.reply_text("Please enter a valid name (1–100 characters).")
        return ONBOARDING_NAME

    context.user_data["onboard_name"] = name
    await update.message.reply_text(
        f"Nice to meet you, {name}! 🙌\n\nWhich city are you in? (e.g. Mumbai, Bangalore)"
    )
    return ONBOARDING_CITY


async def received_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    city = update.message.text.strip().title()
    if not city or len(city) > 100:
        await update.message.reply_text("Please enter a valid city name.")
        return ONBOARDING_CITY

    context.user_data["onboard_city"] = city
    await update.message.reply_text(
        "What's your pincode? I'll use it to find restaurants near you. 📍"
    )
    return ONBOARDING_PINCODE


async def received_pincode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    pincode = update.message.text.strip()
    if not pincode.isdigit() or len(pincode) not in (5, 6):
        await update.message.reply_text("Please enter a valid 6-digit pincode.")
        return ONBOARDING_PINCODE

    context.user_data["onboard_pincode"] = pincode
    await update.message.reply_text(
        "What's your dietary preference?",
        reply_markup=diet_keyboard(),
    )
    return ONBOARDING_DIET


async def received_diet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    query = update.callback_query
    await query.answer()

    diet_map = {"diet:veg": "veg", "diet:nonveg": "nonveg", "diet:vegan": "vegan"}
    diet = diet_map.get(query.data)
    if not diet:
        return ONBOARDING_DIET

    context.user_data["onboard_diet"] = diet
    await query.edit_message_text(
        f"Great choice! One last thing — your timezone.\n\n"
        "Most Indian users are in IST. Tap below or type a timezone like `Asia/Kolkata`.",
        reply_markup=timezone_keyboard(),
        parse_mode="Markdown",
    )
    return ONBOARDING_TIMEZONE


async def received_timezone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    query = update.callback_query
    await query.answer()

    if query.data == "tz:manual":
        await query.edit_message_text(
            "Type your timezone (e.g. `Asia/Kolkata`, `Asia/Calcutta`):",
            parse_mode="Markdown",
        )
        return ONBOARDING_TIMEZONE

    tz = query.data.replace("tz:", "")
    return await _finish_onboarding(update, context, tz, is_callback=True)


async def received_timezone_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    tz = update.message.text.strip()
    return await _finish_onboarding(update, context, tz, is_callback=False)


async def _finish_onboarding(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    timezone: str,
    is_callback: bool,
) -> str:
    try:
        import pytz
        pytz.timezone(timezone)
    except Exception:
        msg = "Invalid timezone. Please try again (e.g. `Asia/Kolkata`):"
        if is_callback:
            await update.callback_query.edit_message_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text(msg, parse_mode="Markdown")
        return ONBOARDING_TIMEZONE

    pool = context.bot_data["db"]
    profile = UserProfile(
        telegram_id=update.effective_user.id,
        name=context.user_data["onboard_name"],
        city=context.user_data["onboard_city"],
        pincode=context.user_data["onboard_pincode"],
        dietary_preference=context.user_data["onboard_diet"],
        timezone=timezone,
    )
    await upsert_user(pool, profile)

    text = (
        f"✅ All set, {profile.name}!\n\n"
        "Here's what you can do:\n"
        "• Just send me what you ate (text or photo 📷)\n"
        "• /suggest — get food suggestions\n"
        "• /calories — today's calorie count\n"
        "• /report — weekly health summary\n\n"
        "Let's start tracking! 🥗"
    )
    if is_callback:
        await update.callback_query.edit_message_text(text)
    else:
        await update.message.reply_text(text)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Onboarding cancelled. Send /start to begin again.")
    return ConversationHandler.END


def build_onboarding_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            ONBOARDING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_name)],
            ONBOARDING_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_city)],
            ONBOARDING_PINCODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_pincode)],
            ONBOARDING_DIET: [CallbackQueryHandler(received_diet, pattern="^diet:")],
            ONBOARDING_TIMEZONE: [
                CallbackQueryHandler(received_timezone_callback, pattern="^tz:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_timezone_text),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
