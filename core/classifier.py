from __future__ import annotations

from typing import Literal


MealType = Literal["breakfast", "lunch", "snacks", "dinner"]


def meal_type_from_hour(hour: int) -> MealType:
    """Determine meal type from the hour (0–23) in the user's local time.

    Windows:
      breakfast : 00:00 – 12:59
      lunch     : 13:00 – 15:59
      snacks    : 16:00 – 18:59
      dinner    : 19:00 – 23:59
    """
    if hour < 13:
        return "breakfast"
    if hour < 16:
        return "lunch"
    if hour < 19:
        return "snacks"
    return "dinner"
