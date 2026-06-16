"""Barcha FSM holatlari (foydalanuvchi va admin uchun)."""

from aiogram.fsm.state import State, StatesGroup


class CaptchaState(StatesGroup):
    waiting = State()


class SearchState(StatesGroup):
    by_name = State()
    by_genre = State()
    by_year = State()
    by_country = State()


class PaymentState(StatesGroup):
    choosing_plan = State()
    waiting_receipt = State()   # karta to'lovi: chek rasmi kutilmoqda


class ContactState(StatesGroup):
    waiting_message = State()    # admin bilan bog'lanish xabari


# ─── ADMIN ───────────────────────────────────────────────────────────────────

class AdminMovie(StatesGroup):
    title = State()
    genre = State()
    country = State()
    year = State()
    rating = State()
    duration = State()
    quality = State()
    code = State()
    file = State()
    vip = State()
    # tahrirlash
    edit_value = State()


class AdminChannel(StatesGroup):
    channel_id = State()
    title = State()
    invite_link = State()
    target = State()


class AdminBroadcast(StatesGroup):
    waiting_content = State()


class AdminAd(StatesGroup):
    content = State()
    button = State()


class AdminUser(StatesGroup):
    search = State()
    give_premium = State()


class AdminReply(StatesGroup):
    waiting_text = State()       # foydalanuvchiga javob
    reject_reason = State()      # to'lovni rad etish sababi


class AdminSettings(StatesGroup):
    edit_value = State()
