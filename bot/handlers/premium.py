"""Premium va to'lov tizimi: karta+chek (admin tasdiqlaydi) va Telegram Payments."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, LabeledPrice, Message, PreCheckoutQuery,
)

from bot.database import requests as db
from bot.keyboards.user import back_to_menu, main_menu, payment_methods, premium_plans
from bot.keyboards.admin import payment_review
from bot.states import PaymentState
from bot.utils import texts
from config import settings

router = Router(name="premium")


@router.callback_query(F.data == "menu:premium")
async def show_premium(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(texts.PREMIUM_INFO, reply_markup=premium_plans(settings.prices))
    await callback.answer()


@router.callback_query(F.data.startswith("plan:"))
async def choose_plan(callback: CallbackQuery) -> None:
    months = int(callback.data.split(":")[1])
    price = settings.prices.get(months, 0)
    await callback.message.edit_text(
        f"💎 <b>{months} oylik Premium</b>\nNarx: <b>{price:,} so'm</b>\n\n"
        f"To'lov usulini tanlang:".replace(",", " "),
        reply_markup=payment_methods(months),
    )
    await callback.answer()


# ─── KARTA + CHEK ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pay_card:"))
async def pay_card(callback: CallbackQuery, state: FSMContext) -> None:
    months = int(callback.data.split(":")[1])
    price = settings.prices.get(months, 0)
    if not settings.card_number:
        await callback.answer("Karta rekvizitlari sozlanmagan. Adminга murojaat qiling.", show_alert=True)
        return
    payment = await db.create_payment(callback.from_user.id, months, price, method="card")
    await state.set_state(PaymentState.waiting_receipt)
    await state.update_data(payment_id=payment.id)
    await callback.message.edit_text(
        f"💳 <b>Karta orqali to'lov</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 Karta: <code>{settings.card_number}</code>\n"
        f"👤 Egasi: {settings.card_holder}\n"
        f"💰 Summa: <b>{price:,} so'm</b>\n\n".replace(",", " ") +
        "To'lovni amalga oshirib, <b>chek rasmini (screenshot)</b> shu yerga yuboring 📤",
        reply_markup=back_to_menu(),
    )
    await callback.answer()


@router.message(PaymentState.waiting_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    payment_id = data.get("payment_id")
    await state.clear()
    if not payment_id:
        await message.answer("⚠️ Xatolik. Qaytadan boshlang.", reply_markup=main_menu())
        return

    file_id = message.photo[-1].file_id
    await db.set_payment_receipt(payment_id, file_id)
    payment = await db.get_payment(payment_id)
    tg = message.from_user

    caption = (
        f"💳 <b>Yangi to'lov cheki</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {tg.full_name} (@{tg.username or 'yoq'})\n"
        f"🆔 <code>{tg.id}</code>\n"
        f"💎 Tarif: {payment.months} oy\n"
        f"💰 Summa: {payment.amount:,} so'm\n"
        f"🧾 To'lov #{payment.id}".replace(",", " ")
    )
    admins = [settings.owner_id] + [a.user_id for a in await db.list_admins()]
    for admin_id in set(admins):
        try:
            await message.bot.send_photo(admin_id, file_id, caption=caption,
                                         reply_markup=payment_review(payment.id))
        except Exception:
            continue
    await db.add_log("payment_submitted", actor_id=tg.id, details=f"#{payment.id} {payment.months}oy")
    await message.answer("✅ Chek yuborildi! Admin tasdiqlagach Premium aktivlashadi.",
                         reply_markup=main_menu())


@router.message(PaymentState.waiting_receipt)
async def receipt_not_photo(message: Message) -> None:
    await message.answer("📤 Iltimos, chek <b>rasmini</b> (screenshot) yuboring.")


# ─── ADMIN TASDIQLASH/RAD ETISH karta to'lovlari uchun premium.py da emas,
#     admin.py da yagona joyda — lekin tasdiqlash mantig'i shu yerda yordamchi:

async def approve_payment_and_notify(bot, payment_id, admin_id) -> bool:
    payment = await db.get_payment(payment_id)
    if not payment or payment.status != "pending":
        return False
    until = await db.grant_premium(payment.user_id, payment.months)
    await db.review_payment(payment_id, "approved", admin_id)
    await db.add_log("payment_approved", actor_id=admin_id, details=f"#{payment_id}")
    try:
        await bot.send_message(
            payment.user_id,
            f"✅ <b>Premium aktivlashtirildi!</b>\n💎 {payment.months} oy\n"
            f"📅 Amal qiladi: {until:%Y-%m-%d}\nRahmat! 🎉"
        )
    except Exception:
        pass
    return True


# ─── AVTOMATIK (Telegram Payments) ───────────────────────────────────────────

@router.callback_query(F.data.startswith("pay_auto:"))
async def pay_auto(callback: CallbackQuery) -> None:
    months = int(callback.data.split(":")[1])
    price = settings.prices.get(months, 0)
    if not settings.payment_provider_token:
        await callback.answer(
            "Avtomatik to'lov hozircha sozlanmagan. Karta orqali to'lang.", show_alert=True
        )
        return
    await callback.message.answer_invoice(
        title=f"Premium {months} oy",
        description=f"Cinema Premium Bot — {months} oylik obuna",
        payload=f"premium:{months}:{callback.from_user.id}",
        provider_token=settings.payment_provider_token,
        currency="UZS",
        prices=[LabeledPrice(label=f"{months} oy Premium", amount=price * 100)],
        start_parameter="premium",
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_paid(message: Message) -> None:
    sp = message.successful_payment
    try:
        _, months_str, _ = sp.invoice_payload.split(":")
        months = int(months_str)
    except Exception:
        months = 1
    until = await db.grant_premium(message.from_user.id, months)
    payment = await db.create_payment(message.from_user.id, months, sp.total_amount // 100, method="telegram")
    await db.review_payment(payment.id, "paid", reviewed_by=0)
    await db.add_log("payment_telegram", actor_id=message.from_user.id, details=f"{months}oy")
    await message.answer(
        f"✅ <b>To'lov muvaffaqiyatli!</b>\n💎 {months} oy Premium aktivlashdi.\n"
        f"📅 Amal qiladi: {until:%Y-%m-%d}\nRahmat! 🎉",
        reply_markup=main_menu(),
    )
