"""/start, captcha, obuna himoyasi, asosiy menyu navigatsiyasi."""

from __future__ import annotations

import logging
import random

from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.database import requests as db
from bot.keyboards.user import main_menu, back_to_menu
from bot.services.subscription import get_unsubscribed_channels
from bot.states import CaptchaState
from bot.utils import texts
from bot.utils.animation import typing_effect
from config import settings

logger = logging.getLogger(__name__)
router = Router(name="start")


def _parse_ref(arg: str | None) -> int | None:
    if not arg:
        return None
    if arg.startswith("ref_"):
        arg = arg[4:]
    return int(arg) if arg.isdigit() else None


async def _send_welcome(message: Message) -> None:
    await typing_effect(message, texts.WELCOME, reply_markup=main_menu())


def _captcha_kb(answer: int):
    opts = {answer, answer + random.randint(1, 5), max(0, answer - random.randint(1, 5))}
    while len(opts) < 3:
        opts.add(answer + random.randint(-7, 7))
    opts = list(opts)
    random.shuffle(opts)
    kb = [[InlineKeyboardButton(text=str(o), callback_data=f"cap:{o}")] for o in opts]
    return InlineKeyboardMarkup(inline_keyboard=kb)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user

    referred_by = _parse_ref(command.args)
    if referred_by == tg.id:
        referred_by = None

    user, created = await db.get_or_create_user(tg.id, tg.username, tg.first_name, referred_by)

    if user.is_banned:
        await message.answer(texts.BANNED)
        return

    # Referal hisobini yangi user uchun qayd qilamiz
    if created and referred_by:
        if await db.add_referral(referred_by, tg.id):
            await _maybe_reward_referrer(message.bot, referred_by)

    if created:
        await db.add_log("user_joined", actor_id=tg.id, details=f"ref={referred_by}")

    # Captcha (faqat o'tmaganlar uchun)
    if not user.is_captcha_passed:
        a, b = random.randint(2, 9), random.randint(2, 9)
        await state.set_state(CaptchaState.waiting)
        await state.update_data(answer=a + b)
        await message.answer(f"{texts.CAPTCHA}\n\n<b>{a} + {b} = ?</b>", reply_markup=_captcha_kb(a + b))
        return

    await _send_welcome(message)


@router.callback_query(CaptchaState.waiting, F.data.startswith("cap:"))
async def captcha_check(callback: CallbackQuery, state: FSMContext) -> None:
    chosen = int(callback.data.split(":")[1])
    data = await state.get_data()
    if chosen != data.get("answer"):
        await callback.answer(texts.CAPTCHA_WRONG, show_alert=True)
        return
    await db.set_captcha_passed(callback.from_user.id)
    await state.clear()
    await callback.message.delete()
    await _send_welcome(callback.message)
    await callback.answer("✅")


async def _maybe_reward_referrer(bot: Bot, referrer_id: int) -> None:
    """Yetarlicha referal yig'ilsa premium kun beradi."""
    n = settings.referrals_per_reward
    unrewarded = await db.count_unrewarded(referrer_id)
    rewards = unrewarded // n
    if rewards <= 0:
        return
    await db.mark_referrals_rewarded(referrer_id, rewards * n)
    until = await db.grant_premium_days(referrer_id, rewards * settings.reward_days)
    try:
        await bot.send_message(
            referrer_id,
            f"🎁 Tabriklaymiz! {rewards * n} ta do'st taklif qildingiz.\n"
            f"Sizga <b>{rewards * settings.reward_days} kun Premium</b> berildi!\n"
            f"Amal qiladi: {until:%Y-%m-%d}"
        )
    except Exception:
        pass


@router.callback_query(F.data == "menu:home")
async def back_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await callback.message.edit_text(texts.WELCOME, reply_markup=main_menu())
    except Exception:
        await callback.message.answer(texts.WELCOME, reply_markup=main_menu())
    await callback.answer()
