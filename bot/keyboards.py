from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def diet_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🥗 Veg", callback_data="diet:veg"),
            InlineKeyboardButton("🍗 Non-Veg", callback_data="diet:nonveg"),
        ],
        [InlineKeyboardButton("🌱 Vegan", callback_data="diet:vegan")],
    ])


def timezone_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇳 IST (India)", callback_data="tz:Asia/Kolkata")],
        [InlineKeyboardButton("🌍 Other (type it)", callback_data="tz:manual")],
    ])


def suggest_health_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Healthy", callback_data="sh:healthy"),
            InlineKeyboardButton("🍕 Indulgent", callback_data="sh:indulgent"),
        ]
    ])


def suggest_method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👨‍🍳 Cook", callback_data="sm:cook"),
            InlineKeyboardButton("🛵 Order", callback_data="sm:order"),
        ]
    ])


def suggest_eat_in_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏠 Deliver to me", callback_data="sei:in"),
            InlineKeyboardButton("🚶 I'll go out", callback_data="sei:out"),
        ]
    ])


def suggest_source_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✨ Something New", callback_data="ss:new"),
            InlineKeyboardButton("📜 From My History", callback_data="ss:history"),
        ]
    ])


def swiggy_link_keyboard(deep_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛵 Order on Swiggy", url=deep_link)]
    ])


def zomato_link_keyboard(deep_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍽️ Search on Zomato", url=deep_link)]
    ])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])
