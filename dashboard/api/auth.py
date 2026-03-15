from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from core.settings import settings


def verify_telegram_login(data: dict) -> bool:
    """Verify Telegram Login Widget data integrity using HMAC-SHA256.

    See https://core.telegram.org/widgets/login#checking-authorization
    """
    check_hash = data.get("hash")
    if not check_hash:
        return False

    # Check data is not stale (max 1 day old)
    auth_date = int(data.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        return False

    # Build data-check-string: sorted key=value pairs excluding hash
    fields = {k: v for k, v in data.items() if k != "hash"}
    data_check_str = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))

    # Secret key = SHA256(bot_token)
    secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_str.encode(), hashlib.sha256).hexdigest()

    return hmac.compare_digest(computed_hash, check_hash)


def create_access_token(telegram_id: int, name: str) -> str:
    """Create a JWT access token for a verified Telegram user."""
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours)
    payload = {
        "sub": str(telegram_id),
        "name": name,
        "exp": expires,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT access token. Returns payload or None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None
