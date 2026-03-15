from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

import pytz

from core.classifier import meal_type_from_hour
from core.models import FoodEntry
from integrations import openai_client

logger = logging.getLogger(__name__)

_TEXT_SYSTEM_PROMPT = """\
You are a food nutrition assistant. The user will describe food they just ate.
Extract the information and return a JSON object with EXACTLY these fields:
{
  "food_name": "concise name of the food (e.g. 'Rajma Chawal', 'Masala Dosa')",
  "calories": <estimated integer calories for one typical serving>,
  "is_healthy": <true if generally considered healthy, false otherwise>
}

Guidelines:
- calories should be realistic for a typical home-cooked or restaurant serving in India
- is_healthy = true for: dal, vegetables, salads, fruits, whole grains, grilled/steamed items
- is_healthy = false for: fried foods, sweets, heavily processed foods, fast food, high-sugar drinks
- If input is unclear, make your best guess
- Return only valid JSON, no extra text
"""

_VISION_SYSTEM_PROMPT = """\
You are a food nutrition assistant analysing a meal photo.
Identify the food(s) in the image and estimate total calories for the entire meal shown.
Return a JSON object with EXACTLY these fields:
{
  "food_name": "concise description of what you see (e.g. 'Butter Chicken with Naan')",
  "calories": <estimated integer total calories for the meal shown>,
  "is_healthy": <true if generally healthy, false otherwise>
}

Return only valid JSON, no extra text.
"""


async def parse_food(
    input_text: Optional[str],
    image_bytes: Optional[bytes],
    timestamp: datetime,
    user_timezone: str = "Asia/Kolkata",
) -> FoodEntry:
    """Parse food from text or image and return a structured FoodEntry.

    Uses GPT-4o-mini for text, GPT-4o vision for images.
    Meal type is determined from the timestamp in the user's local timezone.
    """
    # Determine meal type from timestamp in user's timezone
    try:
        tz = pytz.timezone(user_timezone)
        local_dt = timestamp.astimezone(tz)
    except Exception:
        local_dt = timestamp
    meal_type = meal_type_from_hour(local_dt.hour)

    if image_bytes:
        return await _parse_from_image(image_bytes, meal_type)
    elif input_text:
        return await _parse_from_text(input_text, meal_type)
    else:
        raise ValueError("Either input_text or image_bytes must be provided")


async def _parse_from_text(text: str, meal_type: str) -> FoodEntry:
    messages = [
        {"role": "system", "content": _TEXT_SYSTEM_PROMPT},
        {"role": "user", "content": f"I just ate: {text}"},
    ]
    try:
        result = await openai_client.chat_json(messages, model="gemini-1.5-flash")
        return FoodEntry(
            food_name=result["food_name"],
            calories=int(result["calories"]),
            is_healthy=bool(result["is_healthy"]),
            meal_type=meal_type,
            input_type="text",
            raw_input=text,
        )
    except Exception as e:
        logger.error("Text food parsing failed: %s | input=%r", e, text)
        # Fallback entry so the user still gets a response
        return FoodEntry(
            food_name=text[:100],
            calories=300,
            is_healthy=False,
            meal_type=meal_type,
            input_type="text",
            raw_input=text,
        )


async def _parse_from_image(image_bytes: bytes, meal_type: str) -> FoodEntry:
    try:
        raw = await openai_client.vision(image_bytes, _VISION_SYSTEM_PROMPT)
        result = json.loads(raw)
        return FoodEntry(
            food_name=result["food_name"],
            calories=int(result["calories"]),
            is_healthy=bool(result["is_healthy"]),
            meal_type=meal_type,
            input_type="photo",
            raw_input=None,
        )
    except Exception as e:
        logger.error("Image food parsing failed: %s", e)
        return FoodEntry(
            food_name="Unknown food (photo)",
            calories=400,
            is_healthy=False,
            meal_type=meal_type,
            input_type="photo",
            raw_input=None,
        )
