"""Majburiy obuna xizmati: a'zolikni tekshirish va kanal sanog'ini yangilash."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from bot.database import requests as db

logger = logging.getLogger(__name__)


async def get_unsubscribed_channels(bot: Bot, user_id: int) -> list:
    """Foydalanuvchi obuna BO'LMAGAN faol kanallar ro'yxatini qaytaradi."""
    channels = await db.get_active_channels()
    not_subbed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch.channel_id, user_id)
            if member.status in ("left", "kicked"):
                not_subbed.append(ch)
        except TelegramAPIError:
            # Bot kanalda admin emas yoki kanal yo'q — bu kanalni tekshirmaymiz
            logger.warning("Kanal a'zoligini tekshirib bo'lmadi: %s", ch.channel_id)
            continue
    return not_subbed


async def refresh_channel_counts(bot: Bot) -> None:
    """
    Har bir faol kanal obunachilar sonini yangilaydi.
    Maqsadga (target_count) yetgan kanal majburiy obunadan AVTO o'chiriladi.
    APScheduler orqali har 10 daqiqada chaqiriladi.
    """
    channels = await db.get_active_channels()
    for ch in channels:
        try:
            count = await bot.get_chat_member_count(ch.channel_id)
            await db.update_channel_count(ch.id, count)
            if ch.target_count and count >= ch.target_count:
                await db.deactivate_channel(ch.id)
                await db.add_log("channel_target_reached", details=f"{ch.title} ({count}/{ch.target_count})")
                logger.info("Kanal maqsadga yetdi va o'chirildi: %s (%s)", ch.title, count)
        except TelegramAPIError:
            logger.warning("Kanal sanog'ini olishda xato: %s", ch.channel_id)
            continue
