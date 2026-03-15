from __future__ import annotations

import base64
import json
import logging
from typing import Any, Optional, Type

from openai import AsyncOpenAI
from pydantic import BaseModel

from core.settings import settings

logger = logging.getLogger(__name__)

# Module-level client, initialised once at startup
_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


def init_client(api_key: Optional[str] = None) -> AsyncOpenAI:
    global _client
    _client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
    return _client


async def chat(
    messages: list[dict],
    model: str = "gpt-4o-mini",
    response_format: Optional[dict] = None,
    temperature: float = 0.3,
) -> str:
    """Send a chat completion request and return the response text."""
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        kwargs["response_format"] = response_format

    response = await get_client().chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


async def chat_json(
    messages: list[dict],
    model: str = "gpt-4o-mini",
    temperature: float = 0.1,
) -> dict:
    """Chat completion that always returns parsed JSON."""
    text = await chat(
        messages,
        model=model,
        response_format={"type": "json_object"},
        temperature=temperature,
    )
    return json.loads(text)


async def vision(
    image_bytes: bytes,
    prompt: str,
    model: str = "gpt-4o",
) -> str:
    """Send an image to GPT-4o vision and return the response text."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                },
            ],
        }
    ]
    response = await get_client().chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=512,
    )
    return response.choices[0].message.content or ""
