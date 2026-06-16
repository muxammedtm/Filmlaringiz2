"""Admin inline klaviaturalari."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_panel() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Statistika", callback_data="adm:stats")
    kb.button(text="🎬 Kinolar", callback_data="adm:movies")
    kb.button(text="📡 Kanallar", callback_data="adm:channels")
    kb.button(text="💎 Premium", callback_data="adm:premium")
    kb.button(text="💳 To'lovlar", callback_data="adm:payments")
    kb.button(text="📢 Reklama", callback_data="adm:ads")
    kb.button(text="📨 Broadcast", callback_data="adm:broadcast")
    kb.button(text="👥 Foydalanuvchilar", callback_data="adm:users")
    kb.button(text="🎁 Referal", callback_data="adm:ref")
    kb.button(text="📁 Loglar", callback_data="adm:logs")
    kb.adjust(2, 2, 2, 2, 2)
    return kb.as_markup()


def back_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin panel", callback_data="adm:home")]]
    )


def movies_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Kino qo'shish", callback_data="adm:movie_add")
    kb.button(text="📋 Ro'yxat", callback_data="adm:movie_list:0")
    kb.button(text="🔙 Admin panel", callback_data="adm:home")
    kb.adjust(2, 1)
    return kb.as_markup()


def movie_admin_actions(movie_id) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ O'chirish", callback_data=f"adm:movie_del:{movie_id}")
    kb.button(text="🔙 Orqaga", callback_data="adm:movie_list:0")
    kb.adjust(1)
    return kb.as_markup()


def channels_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Kanal qo'shish", callback_data="adm:ch_add")
    kb.button(text="📋 Ro'yxat", callback_data="adm:ch_list")
    kb.button(text="🔙 Admin panel", callback_data="adm:home")
    kb.adjust(2, 1)
    return kb.as_markup()


def broadcast_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📨 Barchaga", callback_data="adm:bc:all")
    kb.button(text="⭐ Premiumlarga", callback_data="adm:bc:premium")
    kb.button(text="👤 Oddiylarga", callback_data="adm:bc:normal")
    kb.button(text="🔙 Admin panel", callback_data="adm:home")
    kb.adjust(1)
    return kb.as_markup()


def payment_review(payment_id) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"pay_ok:{payment_id}")
    kb.button(text="❌ Bekor qilish", callback_data=f"pay_no:{payment_id}")
    kb.adjust(2)
    return kb.as_markup()


def user_reply_kb(user_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✍️ Javob berish", callback_data=f"ureply:{user_id}")]]
    )


def ads_menu(ads) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Reklama qo'shish", callback_data="adm:ad_add")
    for ad in ads:
        status = "🟢" if ad.is_active else "🔴"
        preview = (ad.text or ad.content_type)[:20]
        kb.button(text=f"{status} {preview} ❌", callback_data=f"adm:ad_del:{ad.id}")
    kb.button(text="🔙 Admin panel", callback_data="adm:home")
    kb.adjust(1)
    return kb.as_markup()
