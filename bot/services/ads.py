"""Reklama ko'rsatish xizmati (faqat oddiy foydalanuvchilarga)."""

from __future__ import annotations

import random

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database import requests as db


async def maybe_show_ad(bot: Bot, user_id: int) -> None:
    """Premium bo'lmaganlarga tasodifiy faol reklama ko'rsatadi."""
    if await db.is_premium(user_id):
        return
    ads = await db.get_active_ads()
    if not ads:
        return
    ad = random.choice(ads)
    markup = None
    if ad.button_text and ad.button_url:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=ad.button_text, url=ad.button_url)]]
        )
    try:
        if ad.content_type == "photo" and ad.file_id:
            await bot.send_photo(user_id, ad.file_id, caption=ad.text or "", reply_markup=markup)
        elif ad.content_type == "video" and ad.file_id:
            await bot.send_video(user_id, ad.file_id, caption=ad.text or "", reply_markup=markup)
        else:
            await bot.send_message(user_id, ad.text or "📢 Reklama", reply_markup=markup)
    except Exception:
        pass
