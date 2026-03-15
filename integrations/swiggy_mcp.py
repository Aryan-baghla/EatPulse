from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from core.models import SwiggyResult
from core.settings import settings

logger = logging.getLogger(__name__)

_SESSION_TTL_HOURS = 24


class SwiggyMCPClient:
    def __init__(self) -> None:
        self.base_url = settings.swiggy_mcp_base_url.rstrip("/")
        self.api_key = settings.swiggy_mcp_api_key

    def _headers(self, session_token: Optional[str] = None) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        if session_token:
            h["Authorization"] = f"Bearer {session_token}"
        return h

    async def initiate_otp(self, phone: str) -> bool:
        """Send OTP to user's phone for Swiggy login. Returns True on success."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.base_url}/auth/otp/send",
                    json={"mobile": phone},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return True
        except httpx.HTTPError as e:
            logger.error("Swiggy OTP send failed: %s", e)
            return False

    async def verify_otp(self, phone: str, otp: str) -> Optional[tuple[str, datetime]]:
        """Verify OTP and return (session_token, expires_at) on success."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.base_url}/auth/otp/verify",
                    json={"mobile": phone, "otp": otp},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                token = data.get("token") or data.get("session_token") or data.get("access_token")
                if not token:
                    logger.error("Swiggy verify OTP: no token in response %s", data)
                    return None
                expires_at = datetime.now(timezone.utc) + timedelta(hours=_SESSION_TTL_HOURS)
                return token, expires_at
        except httpx.HTTPError as e:
            logger.error("Swiggy OTP verify failed: %s", e)
            return None

    async def search(
        self,
        query: str,
        pincode: str,
        session_token: str,
        limit: int = 5,
    ) -> list[SwiggyResult]:
        """Search for restaurants/dishes near the given pincode."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.base_url}/search",
                    params={"q": query, "pincode": pincode, "limit": limit},
                    headers=self._headers(session_token),
                )
                if resp.status_code == 401:
                    logger.warning("Swiggy session expired (401)")
                    return []
                resp.raise_for_status()
                data = resp.json()
                return self._parse_results(data)
        except httpx.HTTPError as e:
            logger.error("Swiggy search failed: %s", e)
            return []

    def _parse_results(self, data: dict) -> list[SwiggyResult]:
        results = []
        items = data.get("results") or data.get("restaurants") or data.get("data") or []
        for item in items:
            try:
                restaurant = item.get("restaurant", item)
                results.append(
                    SwiggyResult(
                        restaurant_name=restaurant.get("name", "Unknown"),
                        dish_name=item.get("dish_name") or item.get("name", ""),
                        rating=float(restaurant.get("avgRating") or restaurant.get("rating") or 0),
                        delivery_time_minutes=int(
                            restaurant.get("sla", {}).get("deliveryTime")
                            or restaurant.get("delivery_time", 30)
                        ),
                        estimated_calories=int(item.get("estimated_calories", 0)),
                        price=int(item.get("price") or item.get("defaultPrice", 0)),
                        deep_link=(
                            f"https://www.swiggy.com/restaurants/{restaurant.get('name','').lower().replace(' ','-')}"
                            f"-{restaurant.get('id','')}"
                        ),
                    )
                )
            except Exception as e:
                logger.debug("Failed to parse Swiggy result item: %s — %s", item, e)
        return results


# Singleton
swiggy_client = SwiggyMCPClient()
