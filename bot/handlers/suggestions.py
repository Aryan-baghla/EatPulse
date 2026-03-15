from __future__ import annotations

import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.keyboards import (
    cancel_keyboard,
    suggest_eat_in_keyboard,
    suggest_health_keyboard,
    suggest_method_keyboard,
    suggest_source_keyboard,
    swiggy_link_keyboard,
    zomato_link_keyboard,
)
from bot.states import (
    SUGGEST_EAT_IN,
    SUGGEST_HEALTH,
    SUGGEST_METHOD,
    SUGGEST_SOURCE,
    SUGGEST_SWIGGY_OTP,
    SUGGEST_SWIGGY_PHONE,
)
from core.models import SuggestionPreferences
from core.suggestion_engine import get_suggestion, _HISTORY_THRESHOLD
from database.queries.food_logs import count_history_entries
from database.queries.suggestions_log import insert_suggestion
from database.queries.users import get_user, update_swiggy_token
from integrations.swiggy_mcp import swiggy_client

logger = logging.getLogger(__name__)


async def cmd_suggest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    pool = context.bot_data["db"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        await update.message.reply_text("Please complete setup first — send /start")
        return ConversationHandler.END

    context.user_data["suggest_user"] = user
    await update.message.reply_text(
        "What kind of food are you in the mood for? 🤔",
        reply_markup=suggest_health_keyboard(),
    )
    return SUGGEST_HEALTH


async def received_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    query = update.callback_query
    await query.answer()

    context.user_data["suggest_healthy"] = query.data == "sh:healthy"
    await query.edit_message_text(
        "How do you want to have it?",
        reply_markup=suggest_method_keyboard(),
    )
    return SUGGEST_METHOD


async def received_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    query = update.callback_query
    await query.answer()

    want_to_cook = query.data == "sm:cook"
    context.user_data["suggest_cook"] = want_to_cook

    if want_to_cook:
        context.user_data["suggest_eat_in"] = True
        await query.edit_message_text(
            "New ideas or from your history?",
            reply_markup=suggest_source_keyboard(),
        )
        return SUGGEST_SOURCE
    else:
        await query.edit_message_text(
            "Want it delivered or will you go out?",
            reply_markup=suggest_eat_in_keyboard(),
        )
        return SUGGEST_EAT_IN


async def received_eat_in(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    query = update.callback_query
    await query.answer()

    context.user_data["suggest_eat_in"] = query.data == "sei:in"
    await query.edit_message_text(
        "New ideas or from your history?",
        reply_markup=suggest_source_keyboard(),
    )
    return SUGGEST_SOURCE


async def received_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    query = update.callback_query
    await query.answer()

    from_history = query.data == "ss:history"
    context.user_data["suggest_from_history"] = from_history

    prefs = SuggestionPreferences(
        want_healthy=context.user_data["suggest_healthy"],
        want_to_cook=context.user_data["suggest_cook"],
        eat_in=context.user_data.get("suggest_eat_in", True),
        from_history=from_history,
    )

    user = context.user_data["suggest_user"]
    pool = context.bot_data["db"]

    # Check if user wants history but has no Swiggy linked
    if not prefs.want_to_cook and not user.swiggy_session_token:
        # Prompt to link Swiggy (non-blocking — user can skip)
        await query.edit_message_text(
            "⚡ Finding suggestions...\n\n"
            "_Tip: Link your Swiggy account with /linkswiggy for live restaurant data!_",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text("⚡ Finding suggestions...")

    timestamp = datetime.now(timezone.utc)
    suggestion = await get_suggestion(profile=user, preferences=prefs, pool=pool, timestamp=timestamp)

    # If from_history returned nothing, it fell back to GPT — update prefs accordingly
    if from_history and not suggestion.items:
        await _send_fallback_notice(query)
        prefs = SuggestionPreferences(
            want_healthy=prefs.want_healthy,
            want_to_cook=prefs.want_to_cook,
            eat_in=prefs.eat_in,
            from_history=False,
        )
        suggestion = await get_suggestion(profile=user, preferences=prefs, pool=pool, timestamp=timestamp)

    # Save to suggestions_log
    suggestion_text = ", ".join(i.name for i in suggestion.items)
    source = "history" if from_history and suggestion.items else "gpt"
    if suggestion.swiggy_results:
        source = "swiggy"
    await insert_suggestion(pool, user.telegram_id, suggestion_text, prefs, source)

    # Build reply text
    lines = ["Here are some ideas for you:\n"]
    for i, item in enumerate(suggestion.items, 1):
        cal_str = f" (~{item.estimated_calories} kcal)" if item.estimated_calories else ""
        lines.append(f"{i}. *{item.name}*{cal_str}")
        if item.description and item.description != "From your history":
            lines.append(f"   _{item.description}_")

    reply_text = "\n".join(lines)

    if suggestion.swiggy_results:
        reply_text += "\n\n🛵 *Ordering options near you:*\n"
        for r in suggestion.swiggy_results[:3]:
            reply_text += (
                f"\n• *{r.restaurant_name}* — {r.dish_name}\n"
                f"  ⭐ {r.rating} | 🕐 {r.delivery_time_minutes} min | ₹{r.price}"
            )
        first = suggestion.swiggy_results[0]
        await query.edit_message_text(reply_text, parse_mode="Markdown")
        await query.message.reply_text(
            "Tap to order 👇",
            reply_markup=swiggy_link_keyboard(first.deep_link),
        )
    elif suggestion.zomato_deep_link:
        await query.edit_message_text(reply_text, parse_mode="Markdown")
        await query.message.reply_text(
            "Search on Zomato 👇",
            reply_markup=zomato_link_keyboard(suggestion.zomato_deep_link),
        )
    else:
        await query.edit_message_text(reply_text, parse_mode="Markdown")

    return ConversationHandler.END


async def _send_fallback_notice(query) -> None:
    try:
        await query.message.reply_text(
            "You don't have enough history yet (need 20+ entries). "
            "Showing AI suggestions instead! ✨"
        )
    except Exception:
        pass


async def cmd_link_swiggy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    pool = context.bot_data["db"]
    user = await get_user(pool, update.effective_user.id)
    if not user:
        await update.message.reply_text("Please complete setup first — send /start")
        return ConversationHandler.END

    context.user_data["swiggy_link_user"] = user
    await update.message.reply_text(
        "To link your Swiggy account, enter your phone number (10 digits):"
    )
    return SUGGEST_SWIGGY_PHONE


async def received_swiggy_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    phone = update.message.text.strip().replace("+91", "").replace(" ", "")
    if not phone.isdigit() or len(phone) != 10:
        await update.message.reply_text("Please enter a valid 10-digit phone number.")
        return SUGGEST_SWIGGY_PHONE

    context.user_data["swiggy_phone"] = phone
    success = await swiggy_client.initiate_otp(phone)
    if not success:
        await update.message.reply_text(
            "Couldn't reach Swiggy right now. Try /linkswiggy later."
        )
        return ConversationHandler.END

    await update.message.reply_text("OTP sent! Enter the 6-digit code from Swiggy:")
    return SUGGEST_SWIGGY_OTP


async def received_swiggy_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    otp = update.message.text.strip()
    phone = context.user_data["swiggy_phone"]
    pool = context.bot_data["db"]
    user = context.user_data["swiggy_link_user"]

    result = await swiggy_client.verify_otp(phone, otp)
    if not result:
        await update.message.reply_text("Invalid OTP. Please try /linkswiggy again.")
        return ConversationHandler.END

    token, expires_at = result
    await update_swiggy_token(pool, user.telegram_id, phone, token, expires_at)
    await update.message.reply_text(
        "✅ Swiggy account linked! Now when you use /suggest to order, "
        "you'll see live restaurant options near you. 🛵"
    )
    return ConversationHandler.END


async def cancel_suggest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Suggestion cancelled.")
    else:
        await update.message.reply_text("Suggestion cancelled.")
    return ConversationHandler.END


def build_suggestions_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("suggest", cmd_suggest)],
        states={
            SUGGEST_HEALTH: [CallbackQueryHandler(received_health, pattern="^sh:")],
            SUGGEST_METHOD: [CallbackQueryHandler(received_method, pattern="^sm:")],
            SUGGEST_EAT_IN: [CallbackQueryHandler(received_eat_in, pattern="^sei:")],
            SUGGEST_SOURCE: [CallbackQueryHandler(received_source, pattern="^ss:")],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_suggest, pattern="^cancel$"),
            CommandHandler("cancel", cancel_suggest),
        ],
        allow_reentry=True,
    )


def build_swiggy_link_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("linkswiggy", cmd_link_swiggy)],
        states={
            SUGGEST_SWIGGY_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_swiggy_phone)
            ],
            SUGGEST_SWIGGY_OTP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_swiggy_otp)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_suggest)],
    )
