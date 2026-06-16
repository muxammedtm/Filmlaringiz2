"""Kino tizimi: kod/nom/janr bo'yicha qidiruv, ko'rish, sevimlilar, TOP, profil, aloqa."""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import requests as db
from bot.keyboards.user import (
    back_to_menu, back_movies_list, main_menu, movie_actions, search_menu,
    subscription_kb,
)
from bot.keyboards.admin import user_reply_kb
from bot.services.subscription import get_unsubscribed_channels
from bot.states import ContactState, SearchState
from bot.utils import texts
from config import settings

router = Router(name="movies")


def _movie_caption(m) -> str:
    parts = [f"🎬 <b>{m.title}</b>"]
    if m.genre:    parts.append(f"🎭 Janr: {m.genre}")
    if m.country:  parts.append(f"🌍 Davlat: {m.country}")
    if m.year:     parts.append(f"📅 Yil: {m.year}")
    if m.rating:   parts.append(f"⭐ Reyting: {m.rating}")
    if m.duration: parts.append(f"⏱ Davomiyligi: {m.duration}")
    if m.quality:  parts.append(f"📺 Sifat: {m.quality}")
    parts.append(f"👁 Ko'rishlar: {m.views}")
    if m.is_vip:   parts.append("💎 <b>VIP</b>")
    return "\n".join(parts)


async def _ensure_subscribed(bot: Bot, user_id: int) -> bool:
    """Premium bo'lmaganlar uchun obunani tekshiradi."""
    if await db.is_premium(user_id):
        return True
    not_subbed = await get_unsubscribed_channels(bot, user_id)
    return len(not_subbed) == 0


# ─── MENYU MARSHRUTLARI ──────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:search")
async def menu_search(callback: CallbackQuery) -> None:
    await callback.message.edit_text("🔍 <b>Qidiruv turini tanlang:</b>", reply_markup=search_menu())
    await callback.answer()


@router.callback_query(F.data == "search:code")
async def search_code(callback: CallbackQuery) -> None:
    await callback.message.edit_text(texts.SEND_CODE, reply_markup=back_to_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("search:"))
async def search_other(callback: CallbackQuery, state: FSMContext) -> None:
    kind = callback.data.split(":")[1]
    if kind == "code":
        return
    prompts = {
        "name": ("📝 Kino nomini yuboring:", SearchState.by_name),
        "genre": ("🎭 Janrni yuboring (masalan: jangari):", SearchState.by_genre),
        "year": ("📅 Yilni yuboring (masalan: 2024):", SearchState.by_year),
        "country": ("🌍 Davlatni yuboring (masalan: AQSH):", SearchState.by_country),
    }
    if kind not in prompts:
        await callback.answer()
        return
    text, st = prompts[kind]
    await state.set_state(st)
    await callback.message.edit_text(text, reply_markup=back_to_menu())
    await callback.answer()


async def _show_results(message: Message, movies) -> None:
    if not movies:
        await message.answer(texts.MOVIE_NOT_FOUND, reply_markup=back_movies_list())
        return
    lines = ["🔎 <b>Topildi:</b>\n"]
    for m in movies[:20]:
        lines.append(f"<code>{m.code}</code> — {m.title} ({m.year or '—'})")
    lines.append("\nKerakli kino <b>kodini</b> yuboring.")
    await message.answer("\n".join(lines), reply_markup=back_movies_list())


@router.message(SearchState.by_name)
async def do_search_name(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _show_results(message, await db.search_movies(name=message.text))


@router.message(SearchState.by_genre)
async def do_search_genre(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _show_results(message, await db.search_movies(genre=message.text))


@router.message(SearchState.by_year)
async def do_search_year(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _show_results(message, await db.search_movies(year=message.text))


@router.message(SearchState.by_country)
async def do_search_country(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _show_results(message, await db.search_movies(country=message.text))


# ─── KOD BO'YICHA (oddiy matn = kod) ─────────────────────────────────────────

@router.message(F.text.regexp(r"^\d{1,8}$"))
async def by_code(message: Message, state: FSMContext) -> None:
    if await state.get_state() is not None:
        return  # boshqa holatda — bu handler ishlamasin
    await db.touch_user(message.from_user.id)
    movie = await db.get_movie_by_code(message.text.strip())
    if not movie:
        await message.answer(texts.MOVIE_NOT_FOUND, reply_markup=back_movies_list())
        return

    if movie.is_vip and not await db.is_premium(message.from_user.id):
        await message.answer(texts.VIP_ONLY, reply_markup=back_to_menu())
        return

    if not await _ensure_subscribed(message.bot, message.from_user.id):
        not_subbed = await get_unsubscribed_channels(message.bot, message.from_user.id)
        await message.answer(texts.SUB_REQUIRED, reply_markup=subscription_kb(not_subbed))
        return

    is_fav = await db.is_favorite(message.from_user.id, movie.id)
    await message.answer(_movie_caption(movie), reply_markup=movie_actions(movie.id, is_fav, bool(movie.file_id)))


# ─── KO'RISH / SEVIMLILAR ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("watch:"))
async def watch(callback: CallbackQuery) -> None:
    movie_id = int(callback.data.split(":")[1])
    movie = await db.get_movie(movie_id)
    if not movie or not movie.file_id:
        await callback.answer("Video topilmadi", show_alert=True)
        return
    if not await _ensure_subscribed(callback.bot, callback.from_user.id):
        not_subbed = await get_unsubscribed_channels(callback.bot, callback.from_user.id)
        await callback.message.answer(texts.SUB_REQUIRED, reply_markup=subscription_kb(not_subbed))
        await callback.answer()
        return
    await db.inc_movie_views(movie_id)
    await db.add_history(callback.from_user.id, movie_id)
    try:
        await callback.message.answer_video(movie.file_id, caption=f"🎬 {movie.title}")
    except Exception:
        await callback.message.answer_document(movie.file_id, caption=f"🎬 {movie.title}")
    await callback.answer()


@router.callback_query(F.data.startswith("fav:"))
async def toggle_fav(callback: CallbackQuery) -> None:
    movie_id = int(callback.data.split(":")[1])
    now_fav = await db.toggle_favorite(callback.from_user.id, movie_id)
    await callback.answer("⭐ Qo'shildi" if now_fav else "🗑 O'chirildi")
    movie = await db.get_movie(movie_id)
    if movie:
        try:
            await callback.message.edit_reply_markup(
                reply_markup=movie_actions(movie_id, now_fav, bool(movie.file_id))
            )
        except Exception:
            pass


# ─── TOP / PROFIL / SEVIMLILAR / ALOQA ───────────────────────────────────────

@router.callback_query(F.data == "menu:top")
async def menu_top(callback: CallbackQuery) -> None:
    movies = await db.top_movies(10)
    if not movies:
        await callback.message.edit_text("Hozircha kinolar yo'q.", reply_markup=back_to_menu())
        await callback.answer()
        return
    lines = ["🔥 <b>TOP 10 kinolar:</b>\n"]
    for i, m in enumerate(movies, 1):
        lines.append(f"{i}. <code>{m.code}</code> — {m.title} (👁 {m.views})")
    await callback.message.edit_text("\n".join(lines), reply_markup=back_to_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:profile")
async def menu_profile(callback: CallbackQuery) -> None:
    u = await db.get_user(callback.from_user.id)
    refs = await db.count_referrals(callback.from_user.id)
    favs = await db.get_favorites(callback.from_user.id)
    hist = await db.get_history(callback.from_user.id, 5)
    prem = "✅ Faol" if (u.is_premium and u.premium_until) else "❌ Yo'q"
    prem_until = f"\n📅 Tugashi: {u.premium_until:%Y-%m-%d}" if (u.is_premium and u.premium_until) else ""
    text = (
        f"👤 <b>Profil</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{u.user_id}</code>\n"
        f"⭐ Premium: {prem}{prem_until}\n"
        f"🎁 Takliflar: {refs} ta\n"
        f"⭐ Sevimlilar: {len(favs)} ta\n"
    )
    if hist:
        text += "\n📜 <b>Oxirgi ko'rganlar:</b>\n" + "\n".join(f"• {m.title}" for m in hist)
    await callback.message.edit_text(text, reply_markup=back_to_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:contact")
async def menu_contact(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ContactState.waiting_message)
    await callback.message.edit_text(texts.CONTACT, reply_markup=back_to_menu())
    await callback.answer()


@router.message(ContactState.waiting_message)
async def contact_send(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    header = (
        f"📨 <b>Yangi murojaat</b>\n"
        f"👤 {tg.full_name}\n"
        f"🔗 @{tg.username or 'yo''q'}\n"
        f"🆔 <code>{tg.id}</code>"
    )
    sent = False
    admins = [settings.owner_id] + [a.user_id for a in await db.list_admins()]
    for admin_id in set(admins):
        try:
            await message.bot.send_message(admin_id, header, reply_markup=user_reply_kb(tg.id))
            await message.bot.copy_message(admin_id, message.chat.id, message.message_id)
            sent = True
        except Exception:
            continue
    await message.answer(texts.CONTACT_SENT if sent else "⚠️ Xatolik. Keyinroq urinib ko'ring.",
                         reply_markup=main_menu())


# ─── OBUNA TEKSHIRISH ────────────────────────────────────────────────────────

@router.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery) -> None:
    not_subbed = await get_unsubscribed_channels(callback.bot, callback.from_user.id)
    if not_subbed:
        await callback.answer(texts.SUB_NOT_DONE, show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=subscription_kb(not_subbed))
        except Exception:
            pass
        return
    await callback.message.edit_text(texts.SUB_OK, reply_markup=main_menu())
    await callback.answer("✅")
