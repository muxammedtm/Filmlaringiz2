"""Foydalanuvchi inline klaviaturalari."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Kino qidirish", callback_data="menu:search")
    kb.button(text="🔥 Mashhur kinolar", callback_data="menu:top")
    kb.button(text="⭐ Premium", callback_data="menu:premium")
    kb.button(text="🎁 Taklifnoma", callback_data="menu:referral")
    kb.button(text="👤 Profil", callback_data="menu:profile")
    kb.button(text="📞 Aloqa", callback_data="menu:contact")
    kb.adjust(1, 2, 2, 1)
    return kb.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="menu:home")]]
    )


def search_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔢 Kod bo'yicha", callback_data="search:code")
    kb.button(text="📝 Nomi bo'yicha", callback_data="search:name")
    kb.button(text="🎭 Janr bo'yicha", callback_data="search:genre")
    kb.button(text="📅 Yil bo'yicha", callback_data="search:year")
    kb.button(text="🌍 Davlat bo'yicha", callback_data="search:country")
    kb.button(text="🔙 Orqaga", callback_data="menu:home")
    kb.adjust(1, 2, 2, 1)
    return kb.as_markup()


def movie_actions(movie_id, is_fav, has_file=True) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if has_file:
        kb.button(text="▶️ Kinoni ko'rish", callback_data=f"watch:{movie_id}")
    fav_text = "🗑 Sevimlilardan o'chir" if is_fav else "⭐ Sevimlilarga qo'sh"
    kb.button(text=fav_text, callback_data=f"fav:{movie_id}")
    kb.button(text="🔙 Asosiy menyu", callback_data="menu:home")
    kb.adjust(1, 1, 1)
    return kb.as_markup()


def subscription_kb(channels) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for ch in channels:
        url = ch.invite_link
        if not url and ch.username:
            url = f"https://t.me/{ch.username.lstrip('@')}"
        if url:
            kb.button(text=f"📢 {ch.title}", url=url)
    kb.button(text="✅ Tekshirish", callback_data="check_sub")
    kb.adjust(1)
    return kb.as_markup()


def premium_plans(prices: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    labels = {1: "1 oy", 3: "3 oy", 6: "6 oy", 12: "12 oy"}
    for months, price in prices.items():
        kb.button(text=f"{labels.get(months, str(months)+' oy')} — {price:,} so'm".replace(",", " "),
                  callback_data=f"plan:{months}")
    kb.button(text="🔙 Asosiy menyu", callback_data="menu:home")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def payment_methods(months) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Karta orqali (chek)", callback_data=f"pay_card:{months}")
    kb.button(text="🤖 Avtomatik to'lov", callback_data=f"pay_auto:{months}")
    kb.button(text="🔙 Orqaga", callback_data="menu:premium")
    kb.adjust(1)
    return kb.as_markup()


def referral_kb(bot_username, ref_code) -> InlineKeyboardMarkup:
    link = f"https://t.me/{bot_username}?start=ref_{ref_code}"
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 Do'stlarga ulashish",
              url=f"https://t.me/share/url?url={link}&text=Premium kinolar boti!")
    kb.button(text="🔙 Asosiy menyu", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


def back_movies_list() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="menu:home")]]
    )
