"""Referal (taklifnoma) bo'limi — foydalanuvchi tomoni."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.database import requests as db
from bot.keyboards.user import referral_kb
from config import settings

router = Router(name="referral")


@router.callback_query(F.data == "menu:referral")
async def show_referral(callback: CallbackQuery) -> None:
    u = await db.get_user(callback.from_user.id)
    total = await db.count_referrals(callback.from_user.id)
    need = settings.referrals_per_reward
    left = (need - (total % need)) % need
    link = f"https://t.me/{settings.bot_username}?start=ref_{u.ref_code}"
    text = (
        "🎁 <b>Taklifnoma tizimi</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"Har <b>{need} ta</b> do'st uchun <b>{settings.reward_days} kun Premium</b>!\n\n"
        f"👥 Takliflaringiz: <b>{total} ta</b>\n"
        f"🎯 Keyingi mukofotgacha: <b>{left or need} ta</b>\n\n"
        f"🔗 <b>Sizning linkingiz:</b>\n<code>{link}</code>"
    )
    await callback.message.edit_text(text, reply_markup=referral_kb(settings.bot_username, u.ref_code))
    await callback.answer()
