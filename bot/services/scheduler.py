"""APScheduler vazifalari: obuna sanog'i va premium muddati eslatmalari."""

from __future__ import annotations

import logging

from aiogram import Bot

from bot.database import requests as db
from bot.services.subscription import refresh_channel_counts

logger = logging.getLogger(__name__)


async def job_refresh_channels(bot: Bot) -> None:
    await refresh_channel_counts(bot)


async def job_premium_reminders(bot: Bot) -> None:
    """Muddat tugashiga 7/3/1 kun qolганlarга eslatma; tugaganlarni oddiyga qaytarish."""
    for days in (7, 3, 1):
        for uid in await db.premiums_expiring_in(days):
            try:
                await bot.send_message(
                    uid,
                    f"⏰ <b>Premium eslatma</b>\nObunangiz tugashiga <b>{days} kun</b> qoldi.\n"
                    f"⭐ Premium bo'limidan uzaytiring."
                )
            except Exception:
                pass

    expired = await db.expire_premiums()
    for uid in expired:
        try:
            await bot.send_message(
                uid, "ℹ️ Premium muddatingiz tugadi. Oddiy tarifga qaytdingiz.\n"
                     "⭐ Yangilash uchun Premium bo'limiga o'ting."
            )
        except Exception:
            pass
    if expired:
        await db.add_log("premium_expired", details=f"{len(expired)} ta")


def setup_scheduler(scheduler, bot: Bot) -> None:
    scheduler.add_job(job_refresh_channels, "interval", minutes=10, args=[bot], id="channels")
    scheduler.add_job(job_premium_reminders, "interval", hours=12, args=[bot], id="premium")
    logger.info("Scheduler vazifalari ro'yxatdan o'tdi (kanallar: 10 daq, premium: 12 soat)")
