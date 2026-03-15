from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from core.models import UserProfile
from dashboard.api.auth import create_access_token, verify_telegram_login
from dashboard.api.dependencies import get_current_user

router = APIRouter(prefix="/api")


@router.post("/auth/telegram")
async def telegram_auth(data: dict) -> dict:
    """Verify Telegram Login Widget data and issue a JWT."""
    if not verify_telegram_login(data):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram login data",
        )

    telegram_id = int(data["id"])
    name = data.get("first_name", "") + " " + data.get("last_name", "")
    token = create_access_token(telegram_id, name.strip())
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
async def get_me(
    user: Annotated[UserProfile, Depends(get_current_user)]
) -> dict:
    return {
        "telegram_id": user.telegram_id,
        "name": user.name,
        "city": user.city,
        "pincode": user.pincode,
        "dietary_preference": user.dietary_preference,
        "timezone": user.timezone,
        "swiggy_linked": bool(user.swiggy_session_token),
    }
