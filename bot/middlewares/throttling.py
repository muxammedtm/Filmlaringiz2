"""
Anti-flood (spam) middleware.

Har bir foydalanuvchining oxirgi xabari vaqtini eslab qoladi va belgilangan
intervaldan tez-tez yuborilgan xabarlarni e'tiborsiz qoldiradi.

Yengil stack uchun xotirada (in-memory) saqlanadi — Redis shart emas.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from config import settings


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate: float | None = None) -> None:
        self.rate = rate if rate is not None else settings.throttle_rate
        self._last_time: dict[int, float] = defaultdict(float)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None:
            now = time.monotonic()
            if now - self._last_time[user.id] < self.rate:
                # Juda tez yuborilgan — e'tiborsiz qoldiramiz (jim)
                return None
            self._last_time[user.id] = now

        return await handler(event, data)
