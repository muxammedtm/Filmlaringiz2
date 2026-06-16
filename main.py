"""
Cinema Premium Bot — kirish nuqtasi.

aiogram 3.x · SQLite · APScheduler — BotHost'ga mos yengil stack.
- long polling (Nginx/webhook shart emas)
- single-instance qulfi (Conflict xatosining oldini oladi)
- anti-flood + ban middleware
- scheduler: kanal sanog'i (10 daq), premium eslatmalari (12 soat)
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import DATA_DIR, settings
from bot.database.base import init_models
from bot.handlers import admin, movies, premium, referral, start
from bot.middlewares.activity import ActivityMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(DATA_DIR, "bot.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

_LOCK_SOCKET: socket.socket | None = None


def _acquire_lock() -> None:
    """Bir vaqtda faqat bitta nusxa ishlashini ta'minlaydi (Conflict himoyasi)."""
    global _LOCK_SOCKET
    _LOCK_SOCKET = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        _LOCK_SOCKET.bind("\0cinema_premium_bot_lock")
    except OSError:
        logger.error("❌ Bot allaqachon ishlamoqda — ikkinchi nusxa to'xtatildi.")
        sys.exit(1)


async def on_startup(bot: Bot) -> None:
    await init_models()
    me = await bot.get_me()
    logger.info("✅ Bot ishga tushdi: @%s (id=%s)", me.username, me.id)


async def main() -> None:
    settings.validate()
    _acquire_lock()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware
    dp.update.middleware(ActivityMiddleware())
    dp.update.middleware(ThrottlingMiddleware())

    # Routerlar (admin birinchi — admin buyruqlari ustun bo'lsin)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(premium.router)
    dp.include_router(referral.router)
    dp.include_router(movies.router)

    # Scheduler
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    setup_scheduler(scheduler, bot)
    scheduler.start()

    dp.startup.register(on_startup)
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
