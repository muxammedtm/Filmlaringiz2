"""
Animatsion xabar effektlari.

`typing_effect` — matnni bo'lak-bo'lak edit qilib, "yozilayotgandek"
ko'rsatadi. Telegram edit limitlariga e'tibor berib, qadamlar soni
cheklangan (aks holda flood-limitга urilamiz).
"""

from __future__ import annotations

import asyncio

from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest


async def typing_effect(
    message: Message,
    final_text: str,
    steps: int = 4,
    delay: float = 0.25,
    **kwargs,
) -> Message:
    """
    Bo'sh (yoki "...") xabardan boshlab, matnni bosqichma-bosqich to'ldiradi.

    message — javob yuboriladigan xabar (foydalanuvchi xabari)
    final_text — yakuniy to'liq matn
    steps — necha bosqichda to'ldirilsin
    delay — bosqichlar orasidagi pauza (sekund)
    """
    # Boshlang'ich xabar
    sent = await message.answer("✨", **{k: v for k, v in kwargs.items() if k != "reply_markup"})

    length = len(final_text)
    if length == 0:
        return sent

    chunk = max(1, length // steps)
    shown = 0

    for i in range(1, steps + 1):
        shown = min(length, chunk * i)
        partial = final_text[:shown]
        try:
            await sent.edit_text(partial)
        except TelegramBadRequest:
            # Matn o'zgarmagan yoki edit imkonsiz — davom etamiz
            pass
        if shown >= length:
            break
        await asyncio.sleep(delay)

    # Yakuniy holatda to'liq matn + klaviatura
    if shown < length or "reply_markup" in kwargs:
        try:
            await sent.edit_text(final_text, reply_markup=kwargs.get("reply_markup"))
        except TelegramBadRequest:
            pass

    return sent
