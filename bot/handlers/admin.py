"""
To'liq admin panel: statistika, kinolar, kanallar, premium, to'lovlar,
reklama, broadcast, foydalanuvchilar, referal, loglar.
Bitta routerda, FSM va callbacklar orqali.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import requests as db
from bot.keyboards.admin import (
    admin_panel, ads_menu, back_admin, broadcast_menu, channels_menu,
    movie_admin_actions, movies_menu, payment_review,
)
from bot.handlers.premium import approve_payment_and_notify
from bot.states import (
    AdminAd, AdminBroadcast, AdminChannel, AdminMovie, AdminReply, AdminUser,
)
from config import settings

logger = logging.getLogger(__name__)
router = Router(name="admin")


async def _guard(event) -> bool:
    uid = event.from_user.id
    return await db.is_admin(uid)


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    if not await _guard(message):
        return
    await state.clear()
    await db.add_log("admin_login", actor_id=message.from_user.id)
    await message.answer("👑 <b>Admin panel</b>", reply_markup=admin_panel())


@router.callback_query(F.data == "adm:home")
async def adm_home(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(callback):
        return
    await state.clear()
    await callback.message.edit_text("👑 <b>Admin panel</b>", reply_markup=admin_panel())
    await callback.answer()


# ─── STATISTIKA ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:stats")
async def adm_stats(callback: CallbackQuery) -> None:
    if not await _guard(callback):
        return
    s = await db.get_stats()
    text = (
        "📊 <b>Statistika</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Jami foydalanuvchilar: <b>{s['total']}</b>\n"
        f"🆕 Bugun qo'shilgan: <b>{s['today']}</b>\n"
        f"🟢 Aktiv (7 kun): <b>{s['active']}</b>\n"
        f"⭐ Premiumlar: <b>{s['premium']}</b>\n"
        f"🎬 Kinolar: <b>{s['movies']}</b>\n"
        f"👁 Jami ko'rishlar: <b>{s['views']}</b>\n"
        f"💰 Daromad: <b>{s['income']:,} so'm</b>".replace(",", " ")
    )
    await callback.message.edit_text(text, reply_markup=back_admin())
    await callback.answer()


# ─── KINOLAR ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:movies")
async def adm_movies(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(callback):
        return
    await state.clear()
    await callback.message.edit_text("🎬 <b>Kinolar boshqaruvi</b>", reply_markup=movies_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:movie_list:"))
async def adm_movie_list(callback: CallbackQuery) -> None:
    if not await _guard(callback):
        return
    movies = await db.list_movies(0, 30)
    if not movies:
        await callback.message.edit_text("Hozircha kino yo'q.", reply_markup=movies_menu())
        await callback.answer()
        return
    lines = ["🎬 <b>Kinolar:</b>\n"]
    for m in movies:
        lines.append(f"<code>{m.code}</code> — {m.title} | o'chirish: /del_{m.id}")
    await callback.message.edit_text("\n".join(lines), reply_markup=movies_menu())
    await callback.answer()


@router.message(F.text.regexp(r"^/del_(\d+)$"))
async def del_movie_cmd(message: Message) -> None:
    if not await _guard(message):
        return
    movie_id = int(message.text.split("_")[1])
    await db.delete_movie(movie_id)
    await db.add_log("movie_deleted", actor_id=message.from_user.id, details=str(movie_id))
    await message.answer("✅ Kino o'chirildi.", reply_markup=movies_menu())


# Kino qo'shish — qadamma-qadam FSM
@router.callback_query(F.data == "adm:movie_add")
async def movie_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(callback):
        return
    await state.set_state(AdminMovie.title)
    await callback.message.edit_text("📝 Kino <b>nomini</b> yuboring:", reply_markup=back_admin())
    await callback.answer()


@router.message(AdminMovie.title)
async def movie_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text)
    await state.set_state(AdminMovie.genre)
    await message.answer("🎭 <b>Janr</b> (yoki /skip):")


@router.message(AdminMovie.genre)
async def movie_genre(message: Message, state: FSMContext) -> None:
    await state.update_data(genre=None if message.text == "/skip" else message.text)
    await state.set_state(AdminMovie.country)
    await message.answer("🌍 <b>Davlat</b> (yoki /skip):")


@router.message(AdminMovie.country)
async def movie_country(message: Message, state: FSMContext) -> None:
    await state.update_data(country=None if message.text == "/skip" else message.text)
    await state.set_state(AdminMovie.year)
    await message.answer("📅 <b>Yil</b> (yoki /skip):")


@router.message(AdminMovie.year)
async def movie_year(message: Message, state: FSMContext) -> None:
    year = int(message.text) if message.text.isdigit() else None
    await state.update_data(year=year)
    await state.set_state(AdminMovie.rating)
    await message.answer("⭐ <b>Reyting</b> (masalan 8.5, yoki /skip):")


@router.message(AdminMovie.rating)
async def movie_rating(message: Message, state: FSMContext) -> None:
    await state.update_data(rating=None if message.text == "/skip" else message.text)
    await state.set_state(AdminMovie.duration)
    await message.answer("⏱ <b>Davomiyligi</b> (masalan 2s 10daq, yoki /skip):")


@router.message(AdminMovie.duration)
async def movie_duration(message: Message, state: FSMContext) -> None:
    await state.update_data(duration=None if message.text == "/skip" else message.text)
    await state.set_state(AdminMovie.quality)
    await message.answer("📺 <b>Sifat</b> (4K/FullHD/HD, yoki /skip):")


@router.message(AdminMovie.quality)
async def movie_quality(message: Message, state: FSMContext) -> None:
    await state.update_data(quality=None if message.text == "/skip" else message.text)
    await state.set_state(AdminMovie.code)
    await message.answer("🔢 <b>Kod</b> (masalan 1234):")


@router.message(AdminMovie.code)
async def movie_code(message: Message, state: FSMContext) -> None:
    code = message.text.strip()
    if await db.get_movie_by_code(code):
        await message.answer("❌ Bu kod band. Boshqa kod yuboring:")
        return
    await state.update_data(code=code)
    await state.set_state(AdminMovie.vip)
    await message.answer("💎 VIP (faqat premium) bo'lsinmi? <b>ha</b> / <b>yoq</b>:")


@router.message(AdminMovie.vip)
async def movie_vip(message: Message, state: FSMContext) -> None:
    await state.update_data(is_vip=message.text.strip().lower() in ("ha", "yes", "ha'"))
    await state.set_state(AdminMovie.file)
    await message.answer("🎬 Endi <b>video yoki faylni</b> yuboring:")


@router.message(AdminMovie.file, F.video | F.document)
async def movie_file(message: Message, state: FSMContext) -> None:
    file_id = message.video.file_id if message.video else message.document.file_id
    data = await state.get_data()
    await state.clear()
    data["file_id"] = file_id
    movie = await db.add_movie(data)
    await db.add_log("movie_added", actor_id=message.from_user.id, details=f"{movie.code} {movie.title}")
    await message.answer(
        f"✅ Kino qo'shildi!\n🎬 {movie.title}\n🔢 Kod: <code>{movie.code}</code>",
        reply_markup=movies_menu(),
    )


@router.message(AdminMovie.file)
async def movie_file_invalid(message: Message) -> None:
    await message.answer("📤 Video yoki fayl yuboring.")


# ─── KANALLAR ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:channels")
async def adm_channels(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(callback):
        return
    await state.clear()
    await callback.message.edit_text("📡 <b>Majburiy obuna kanallari</b>", reply_markup=channels_menu())
    await callback.answer()


@router.callback_query(F.data == "adm:ch_list")
async def adm_ch_list(callback: CallbackQuery) -> None:
    if not await _guard(callback):
        return
    channels = await db.get_all_channels()
    if not channels:
        await callback.message.edit_text("Kanal yo'q.", reply_markup=channels_menu())
        await callback.answer()
        return
    lines = ["📡 <b>Kanallar:</b>\n"]
    for c in channels:
        st = "🟢" if c.is_active else "🔴"
        tgt = f"{c.current_count}/{c.target_count}" if c.target_count else f"{c.current_count}/∞"
        lines.append(f"{st} {c.title} ({tgt}) | o'chirish: /chdel_{c.id}")
    await callback.message.edit_text("\n".join(lines), reply_markup=channels_menu())
    await callback.answer()


@router.message(F.text.regexp(r"^/chdel_(\d+)$"))
async def ch_del(message: Message) -> None:
    if not await _guard(message):
        return
    cid = int(message.text.split("_")[1])
    await db.delete_channel(cid)
    await message.answer("✅ Kanal o'chirildi.", reply_markup=channels_menu())


@router.callback_query(F.data == "adm:ch_add")
async def ch_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(callback):
        return
    await state.set_state(AdminChannel.channel_id)
    await callback.message.edit_text(
        "📡 Kanal <b>ID</b> yoki <b>@username</b> ni yuboring.\n"
        "⚠️ Bot kanalda <b>admin</b> bo'lishi shart!", reply_markup=back_admin())
    await callback.answer()


@router.message(AdminChannel.channel_id)
async def ch_id(message: Message, state: FSMContext) -> None:
    await state.update_data(channel_id=message.text.strip())
    await state.set_state(AdminChannel.title)
    await message.answer("📝 Kanal <b>nomini</b> yuboring:")


@router.message(AdminChannel.title)
async def ch_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text)
    await state.set_state(AdminChannel.invite_link)
    await message.answer("🔗 <b>Invite link</b> yuboring (yoki /skip):")


@router.message(AdminChannel.invite_link)
async def ch_link(message: Message, state: FSMContext) -> None:
    link = None if message.text == "/skip" else message.text.strip()
    await state.update_data(invite_link=link)
    await state.set_state(AdminChannel.target)
    await message.answer("🎯 <b>Maqsad</b> (necha obunachida o'chsin? 0 = cheksiz):")


@router.message(AdminChannel.target)
async def ch_target(message: Message, state: FSMContext) -> None:
    target = int(message.text) if message.text.strip().isdigit() else 0
    data = await state.get_data()
    await state.clear()
    username = data["channel_id"] if data["channel_id"].startswith("@") else None
    await db.add_channel({
        "channel_id": data["channel_id"], "username": username,
        "title": data["title"], "invite_link": data.get("invite_link"),
        "target_count": target,
    })
    await db.add_log("channel_added", actor_id=message.from_user.id, details=data["title"])
    await message.answer("✅ Kanal qo'shildi.", reply_markup=channels_menu())


# ─── TO'LOVLAR (tasdiqlash/rad etish) ────────────────────────────────────────

@router.callback_query(F.data == "adm:payments")
async def adm_payments(callback: CallbackQuery) -> None:
    if not await _guard(callback):
        return
    await callback.message.edit_text(
        "💳 <b>To'lovlar</b>\nYangi cheklar kelganda shu yerга keladi va tasdiqlash tugmasi bo'ladi.",
        reply_markup=back_admin())
    await callback.answer()


@router.callback_query(F.data.startswith("pay_ok:"))
async def pay_approve(callback: CallbackQuery) -> None:
    if not await _guard(callback):
        return
    pid = int(callback.data.split(":")[1])
    ok = await approve_payment_and_notify(callback.bot, pid, callback.from_user.id)
    await callback.answer("✅ Tasdiqlandi" if ok else "Allaqachon ko'rib chiqilgan", show_alert=not ok)
    if ok:
        try:
            await callback.message.edit_caption(
                caption=(callback.message.caption or "") + "\n\n✅ <b>TASDIQLANDI</b>")
        except Exception:
            pass


@router.callback_query(F.data.startswith("pay_no:"))
async def pay_reject(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(callback):
        return
    pid = int(callback.data.split(":")[1])
    await state.set_state(AdminReply.reject_reason)
    await state.update_data(payment_id=pid)
    await callback.message.answer("❌ Rad etish <b>sababini</b> yozing:")
    await callback.answer()


@router.message(AdminReply.reject_reason)
async def pay_reject_reason(message: Message, state: FSMContext) -> None:
    if not await _guard(message):
        return
    data = await state.get_data()
    await state.clear()
    pid = data.get("payment_id")
    payment = await db.get_payment(pid)
    if payment and payment.status == "pending":
        await db.review_payment(pid, "rejected", message.from_user.id, reason=message.text)
        await db.add_log("payment_rejected", actor_id=message.from_user.id, details=f"#{pid}")
        try:
            await message.bot.send_message(
                payment.user_id, f"❌ To'lovingiz bekor qilindi.\nSabab: {message.text}")
        except Exception:
            pass
    await message.answer("✅ Rad etildi va foydalanuvchiga xabar berildi.", reply_markup=admin_panel())


# ─── FOYDALANUVCHIGA JAVOB (aloqa) ───────────────────────────────────────────

@router.callback_query(F.data.startswith("ureply:"))
async def user_reply_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(callback):
        return
    uid = int(callback.data.split(":")[1])
    await state.set_state(AdminReply.waiting_text)
    await state.update_data(target=uid)
    await callback.message.answer("✍️ Javob matnini yozing:")
    await callback.answer()


@router.message(AdminReply.waiting_text)
async def user_reply_send(message: Message, state: FSMContext) -> None:
    if not await _guard(message):
        return
    data = await state.get_data()
    await state.clear()
    uid = data.get("target")
    try:
        await message.bot.send_message(uid, f"📩 <b>Admin javobi:</b>\n\n{message.text}")
        await message.answer("✅ Yuborildi.")
    except Exception:
        await message.answer("⚠️ Yuborib bo'lmadi (foydalanuvchi botni bloklagan bo'lishi mumkin).")


# ─── PREMIUM (qo'lda berish) ─────────────────────────────────────────────────

@router.callback_query(F.data == "adm:premium")
async def adm_premium(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(callback):
        return
    await state.set_state(AdminUser.give_premium)
    await callback.message.edit_text(
        "💎 Premium berish.\nFormat: <code>user_id oylar</code>\nMasalan: <code>123456789 3</code>",
        reply_markup=back_admin())
    await callback.answer()


@router.message(AdminUser.give_premium)
async def give_premium(message: Message, state: FSMContext) -> None:
    if not await _guard(message):
        return
    await state.clear()
    parts = message.text.split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("❌ Format xato. Masalan: 123456789 3", reply_markup=back_admin())
        return
    uid, months = int(parts[0]), int(parts[1])
    until = await db.grant_premium(uid, months)
    await db.add_log("premium_granted", actor_id=message.from_user.id, details=f"{uid} {months}oy")
    try:
        await message.bot.send_message(uid, f"🎁 Sizga {months} oy Premium berildi!\n📅 {until:%Y-%m-%d}")
    except Exception:
        pass
    await message.answer(f"✅ {uid} ga {months} oy premium berildi.", reply_markup=admin_panel())


# ─── FOYDALANUVCHILAR (qidiruv, ban) ─────────────────────────────────────────

@router.callback_query(F.data == "adm:users")
async def adm_users(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(callback):
        return
    await state.set_state(AdminUser.search)
    await callback.message.edit_text(
        "👥 Foydalanuvchini qidirish: <b>ID</b> yoki <b>@username</b> yuboring.",
        reply_markup=back_admin())
    await callback.answer()


@router.message(AdminUser.search)
async def user_search(message: Message, state: FSMContext) -> None:
    if not await _guard(message):
        return
    await state.clear()
    user = await db.find_user(message.text)
    if not user:
        await message.answer("❌ Topilmadi.", reply_markup=admin_panel())
        return
    prem = "✅" if user.is_premium else "❌"
    ban_cmd = f"/unban_{user.user_id}" if user.is_banned else f"/ban_{user.user_id}"
    ban_lbl = "Blokdan chiqarish" if user.is_banned else "Bloklash"
    await message.answer(
        f"👤 <b>{user.first_name}</b>\n🆔 <code>{user.user_id}</code>\n"
        f"🔗 @{user.username or 'yoq'}\n⭐ Premium: {prem}\n"
        f"🚫 Ban: {'Ha' if user.is_banned else 'Yoq'}\n\n"
        f"{ban_lbl}: {ban_cmd}",
        reply_markup=admin_panel())


@router.message(F.text.regexp(r"^/ban_(\d+)$"))
async def ban_user(message: Message) -> None:
    if not await _guard(message):
        return
    uid = int(message.text.split("_")[1])
    await db.set_banned(uid, True)
    await db.add_log("user_banned", actor_id=message.from_user.id, details=str(uid))
    await message.answer(f"🚫 {uid} bloklandi.")


@router.message(F.text.regexp(r"^/unban_(\d+)$"))
async def unban_user(message: Message) -> None:
    if not await _guard(message):
        return
    uid = int(message.text.split("_")[1])
    await db.set_banned(uid, False)
    await message.answer(f"✅ {uid} blokdan chiqarildi.")


# ─── REKLAMA ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:ads")
async def adm_ads(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(callback):
        return
    await state.clear()
    ads = await db.get_all_ads()
    await callback.message.edit_text(
        "📢 <b>Reklamalar</b>\n🟢 faol  🔴 o'chiq\nO'chirish uchun ustiga bosing.",
        reply_markup=ads_menu(ads))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:ad_del:"))
async def ad_del(callback: CallbackQuery) -> None:
    if not await _guard(callback):
        return
    await db.delete_ad(int(callback.data.split(":")[2]))
    ads = await db.get_all_ads()
    await callback.message.edit_text("✅ O'chirildi.\n\n📢 <b>Reklamalar</b>", reply_markup=ads_menu(ads))
    await callback.answer()


@router.callback_query(F.data == "adm:ad_add")
async def ad_add(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(callback):
        return
    await state.set_state(AdminAd.content)
    await callback.message.edit_text(
        "📢 Reklama <b>matnini</b> yuboring (yoki rasm/video + izoh):",
        reply_markup=back_admin())
    await callback.answer()


@router.message(AdminAd.content)
async def ad_content(message: Message, state: FSMContext) -> None:
    if not await _guard(message):
        return
    data = {"content_type": "text", "text": message.text or message.caption}
    if message.photo:
        data = {"content_type": "photo", "file_id": message.photo[-1].file_id, "text": message.caption}
    elif message.video:
        data = {"content_type": "video", "file_id": message.video.file_id, "text": message.caption}
    await state.update_data(ad=data)
    await state.set_state(AdminAd.button)
    await message.answer("🔘 Tugma kerakmi? Format: <code>Matn | https://link</code>\nKerak bo'lmasa /skip")


@router.message(AdminAd.button)
async def ad_button(message: Message, state: FSMContext) -> None:
    if not await _guard(message):
        return
    data = await state.get_data()
    ad = data["ad"]
    if message.text != "/skip" and "|" in message.text:
        btn_text, btn_url = [x.strip() for x in message.text.split("|", 1)]
        ad["button_text"], ad["button_url"] = btn_text, btn_url
    await state.clear()
    await db.add_ad(ad)
    await db.add_log("ad_added", actor_id=message.from_user.id)
    await message.answer("✅ Reklama qo'shildi.", reply_markup=admin_panel())


# ─── BROADCAST ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:broadcast")
async def adm_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(callback):
        return
    await state.clear()
    await callback.message.edit_text("📨 <b>Broadcast</b>\nKimga yuborilsin?", reply_markup=broadcast_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:bc:"))
async def bc_target(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _guard(callback):
        return
    target = callback.data.split(":")[2]
    await state.set_state(AdminBroadcast.waiting_content)
    await state.update_data(target=target)
    await callback.message.edit_text(
        "📨 Yuboriladigan <b>xabarni</b> yuboring (matn/rasm/video):", reply_markup=back_admin())
    await callback.answer()


@router.message(AdminBroadcast.waiting_content)
async def bc_send(message: Message, state: FSMContext, bot: Bot) -> None:
    if not await _guard(message):
        return
    data = await state.get_data()
    await state.clear()
    target = data.get("target", "all")
    flag = {"all": None, "premium": True, "normal": False}.get(target)
    ids = await db.all_user_ids(only_premium=flag)
    await message.answer(f"📨 Yuborilmoqda... ({len(ids)} ta)")

    sent = fail = 0
    for uid in ids:
        try:
            await bot.copy_message(uid, message.chat.id, message.message_id)
            sent += 1
        except Exception:
            fail += 1
        if (sent + fail) % 25 == 0:
            await asyncio.sleep(1)  # flood-limit oldini olish
    await db.add_log("broadcast", actor_id=message.from_user.id, details=f"{sent}/{len(ids)}")
    await message.answer(f"✅ Tugadi.\n📤 Yuborildi: {sent}\n❌ Xato: {fail}", reply_markup=admin_panel())


# ─── REFERAL (umumiy) / LOGLAR ───────────────────────────────────────────────

@router.callback_query(F.data == "adm:ref")
async def adm_ref(callback: CallbackQuery) -> None:
    if not await _guard(callback):
        return
    await callback.message.edit_text(
        f"🎁 <b>Referal tizimi</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"Har <b>{settings.referrals_per_reward}</b> ta taklif uchun "
        f"<b>{settings.reward_days} kun</b> premium.\n\n"
        f"Sozlamalar .env orqali (REFERRALS_PER_REWARD, REWARD_DAYS).",
        reply_markup=back_admin())
    await callback.answer()


@router.callback_query(F.data == "adm:logs")
async def adm_logs(callback: CallbackQuery) -> None:
    if not await _guard(callback):
        return
    logs = await db.get_logs(25)
    if not logs:
        await callback.message.edit_text("Log yo'q.", reply_markup=back_admin())
        await callback.answer()
        return
    lines = ["📁 <b>Oxirgi loglar:</b>\n"]
    for lg in logs:
        lines.append(f"<code>{lg.created_at:%m-%d %H:%M}</code> {lg.action} "
                     f"{('('+str(lg.actor_id)+')') if lg.actor_id else ''} {lg.details or ''}")
    await callback.message.edit_text("\n".join(lines)[:4000], reply_markup=back_admin())
    await callback.answer()
