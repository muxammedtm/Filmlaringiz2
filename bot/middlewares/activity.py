"""Faollik + ban tekshiruvi middleware (har bir update uchun)."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.database import requests as db


class ActivityMiddleware(BaseMiddleware):
    """Banlangan foydalanuvchini to'sadi va faollikni belgilaydi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None and not user.is_bot:
            if await db.is_banned(user.id):
                return None  # banlangan — e'tiborsiz
        return await handler(event, data)
