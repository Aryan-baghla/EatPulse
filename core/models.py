from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    telegram_id: int
    name: str
    city: str
    pincode: str
    dietary_preference: Literal["veg", "nonveg", "vegan"]
    timezone: str = "Asia/Kolkata"
    swiggy_phone: Optional[str] = None
    swiggy_session_token: Optional[str] = None
    created_at: Optional[datetime] = None


class FoodEntry(BaseModel):
    food_name: str
    calories: int = Field(ge=0)
    is_healthy: bool
    meal_type: Literal["breakfast", "lunch", "snacks", "dinner"]
    input_type: Literal["text", "photo"]
    raw_input: Optional[str] = None


class SuggestionPreferences(BaseModel):
    want_healthy: bool
    want_to_cook: bool        # False = order/go out
    eat_in: bool = True       # True = order in, False = go out (only when want_to_cook=False)
    from_history: bool = False


class SuggestedItem(BaseModel):
    name: str
    description: str
    estimated_calories: int
    source: Literal["gpt", "history"]


class SwiggyResult(BaseModel):
    restaurant_name: str
    dish_name: str
    rating: float
    delivery_time_minutes: int
    estimated_calories: int
    price: int
    deep_link: str


class Suggestion(BaseModel):
    items: list[SuggestedItem]
    swiggy_results: list[SwiggyResult] = []
    zomato_deep_link: Optional[str] = None


class WeeklyReportStats(BaseModel):
    user_id: int
    week_start: str          # YYYY-MM-DD
    week_end: str
    total_calories: int
    daily_calories: dict[str, int]  # date string → calories
    healthy_count: int
    unhealthy_count: int
    healthy_pct: float
    top_foods: list[str]
    health_score: float      # 1–10
    prev_health_score: Optional[float] = None
