"""
Repository qatlami — barcha ma'lumotlar bazasi amallari shu yerda jamlangan.
Handlerlar to'g'ridan-to'g'ri SQL yozmaydi, faqat shu funksiyalarni chaqiradi.
"""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select, update

from bot.database.base import async_session
from bot.database.models import (
    Admin, Advertisement, Category, Channel, Favorite, History,
    Log, Movie, Payment, Referral, Setting, User,
)
from config import settings


def _gen_code(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


# ═══════════════════════════════ USERS ═══════════════════════════════════════

async def get_or_create_user(user_id, username, first_name, referred_by=None):
    async with async_session() as s:
        user = await s.get(User, user_id)
        created = False
        if user is None:
            user = User(
                user_id=user_id, username=username, first_name=first_name,
                ref_code=_gen_code(), referred_by=referred_by,
            )
            s.add(user)
            created = True
        else:
            user.username = username
            user.first_name = first_name
            user.last_active = datetime.utcnow()
        await s.commit()
        await s.refresh(user)
        return user, created


async def get_user(user_id) -> User | None:
    async with async_session() as s:
        return await s.get(User, user_id)


async def touch_user(user_id) -> None:
    async with async_session() as s:
        await s.execute(update(User).where(User.user_id == user_id).values(last_active=datetime.utcnow()))
        await s.commit()


async def set_captcha_passed(user_id) -> None:
    async with async_session() as s:
        await s.execute(update(User).where(User.user_id == user_id).values(is_captcha_passed=True))
        await s.commit()


async def set_banned(user_id, banned: bool) -> None:
    async with async_session() as s:
        await s.execute(update(User).where(User.user_id == user_id).values(is_banned=banned))
        await s.commit()


async def is_banned(user_id) -> bool:
    u = await get_user(user_id)
    return bool(u and u.is_banned)


async def find_user(query: str) -> User | None:
    """ID yoki @username bo'yicha qidiradi."""
    q = query.strip().lstrip("@")
    async with async_session() as s:
        if q.isdigit():
            return await s.get(User, int(q))
        res = await s.execute(select(User).where(User.username == q))
        return res.scalar_one_or_none()


async def list_users(offset=0, limit=10):
    async with async_session() as s:
        res = await s.execute(select(User).order_by(User.created_at.desc()).offset(offset).limit(limit))
        return res.scalars().all()


async def all_user_ids(only_premium=None) -> list[int]:
    async with async_session() as s:
        stmt = select(User.user_id).where(User.is_banned == False)  # noqa: E712
        if only_premium is True:
            stmt = stmt.where(User.is_premium == True)  # noqa: E712
        elif only_premium is False:
            stmt = stmt.where(User.is_premium == False)  # noqa: E712
        res = await s.execute(stmt)
        return [r[0] for r in res.all()]


# ═══════════════════════════════ PREMIUM ═════════════════════════════════════

async def grant_premium(user_id, months: int) -> datetime:
    async with async_session() as s:
        user = await s.get(User, user_id)
        now = datetime.utcnow()
        base = user.premium_until if (user and user.premium_until and user.premium_until > now) else now
        new_until = base + timedelta(days=30 * months)
        await s.execute(update(User).where(User.user_id == user_id).values(is_premium=True, premium_until=new_until))
        await s.commit()
        return new_until


async def grant_premium_days(user_id, days: int) -> datetime:
    async with async_session() as s:
        user = await s.get(User, user_id)
        now = datetime.utcnow()
        base = user.premium_until if (user and user.premium_until and user.premium_until > now) else now
        new_until = base + timedelta(days=days)
        await s.execute(update(User).where(User.user_id == user_id).values(is_premium=True, premium_until=new_until))
        await s.commit()
        return new_until


async def is_premium(user_id) -> bool:
    u = await get_user(user_id)
    return bool(u and u.is_premium and u.premium_until and u.premium_until > datetime.utcnow())


async def expire_premiums() -> list[int]:
    """Muddati tugaganlarni oddiyga qaytaradi. Tugaganlar ID ro'yxatini qaytaradi."""
    now = datetime.utcnow()
    async with async_session() as s:
        res = await s.execute(
            select(User.user_id).where(User.is_premium == True, User.premium_until <= now)  # noqa: E712
        )
        ids = [r[0] for r in res.all()]
        if ids:
            await s.execute(update(User).where(User.user_id.in_(ids)).values(is_premium=False))
            await s.commit()
        return ids


async def premiums_expiring_in(days: int) -> list[int]:
    """Aniq `days` kundan keyin tugaydiganlar (eslatma uchun)."""
    now = datetime.utcnow()
    start = now + timedelta(days=days)
    end = start + timedelta(days=1)
    async with async_session() as s:
        res = await s.execute(
            select(User.user_id).where(
                User.is_premium == True,  # noqa: E712
                User.premium_until >= start, User.premium_until < end,
            )
        )
        return [r[0] for r in res.all()]


# ═══════════════════════════════ MOVIES ══════════════════════════════════════

async def add_movie(data: dict) -> Movie:
    async with async_session() as s:
        movie = Movie(**data)
        s.add(movie)
        await s.commit()
        await s.refresh(movie)
        return movie


async def get_movie_by_code(code: str) -> Movie | None:
    async with async_session() as s:
        res = await s.execute(select(Movie).where(Movie.code == code.strip()))
        return res.scalar_one_or_none()


async def get_movie(movie_id) -> Movie | None:
    async with async_session() as s:
        return await s.get(Movie, movie_id)


async def delete_movie(movie_id) -> None:
    async with async_session() as s:
        await s.execute(delete(Movie).where(Movie.id == movie_id))
        await s.commit()


async def update_movie_field(movie_id, field: str, value) -> None:
    async with async_session() as s:
        await s.execute(update(Movie).where(Movie.id == movie_id).values({field: value}))
        await s.commit()


async def inc_movie_views(movie_id) -> None:
    async with async_session() as s:
        await s.execute(update(Movie).where(Movie.id == movie_id).values(views=Movie.views + 1))
        await s.commit()


async def list_movies(offset=0, limit=10):
    async with async_session() as s:
        res = await s.execute(select(Movie).order_by(Movie.id.desc()).offset(offset).limit(limit))
        return res.scalars().all()


async def top_movies(limit=10):
    async with async_session() as s:
        res = await s.execute(select(Movie).order_by(Movie.views.desc()).limit(limit))
        return res.scalars().all()


async def search_movies(*, name=None, genre=None, year=None, country=None, limit=20):
    async with async_session() as s:
        stmt = select(Movie)
        if name:
            stmt = stmt.where(Movie.title.ilike(f"%{name}%"))
        if genre:
            stmt = stmt.where(Movie.genre.ilike(f"%{genre}%"))
        if year and str(year).isdigit():
            stmt = stmt.where(Movie.year == int(year))
        if country:
            stmt = stmt.where(Movie.country.ilike(f"%{country}%"))
        res = await s.execute(stmt.limit(limit))
        return res.scalars().all()


async def movies_count() -> int:
    async with async_session() as s:
        return (await s.execute(select(func.count(Movie.id)))).scalar() or 0


# ═══════════════════════════ FAVORITES / HISTORY ═════════════════════════════

async def toggle_favorite(user_id, movie_id) -> bool:
    """Qo'shadi yoki o'chiradi. Hozir sevimli bo'lsa True qaytaradi."""
    async with async_session() as s:
        res = await s.execute(
            select(Favorite).where(Favorite.user_id == user_id, Favorite.movie_id == movie_id)
        )
        fav = res.scalar_one_or_none()
        if fav:
            await s.delete(fav)
            await s.commit()
            return False
        s.add(Favorite(user_id=user_id, movie_id=movie_id))
        await s.commit()
        return True


async def is_favorite(user_id, movie_id) -> bool:
    async with async_session() as s:
        res = await s.execute(
            select(Favorite).where(Favorite.user_id == user_id, Favorite.movie_id == movie_id)
        )
        return res.scalar_one_or_none() is not None


async def get_favorites(user_id):
    async with async_session() as s:
        res = await s.execute(
            select(Movie).join(Favorite, Favorite.movie_id == Movie.id)
            .where(Favorite.user_id == user_id).order_by(Favorite.created_at.desc())
        )
        return res.scalars().all()


async def add_history(user_id, movie_id) -> None:
    async with async_session() as s:
        s.add(History(user_id=user_id, movie_id=movie_id))
        await s.commit()


async def get_history(user_id, limit=10):
    async with async_session() as s:
        res = await s.execute(
            select(Movie).join(History, History.movie_id == Movie.id)
            .where(History.user_id == user_id).order_by(History.created_at.desc()).limit(limit)
        )
        return res.scalars().all()


# ═══════════════════════════════ CHANNELS ════════════════════════════════════

async def add_channel(data: dict) -> Channel:
    async with async_session() as s:
        ch = Channel(**data)
        s.add(ch)
        await s.commit()
        await s.refresh(ch)
        return ch


async def get_active_channels():
    async with async_session() as s:
        res = await s.execute(select(Channel).where(Channel.is_active == True))  # noqa: E712
        return res.scalars().all()


async def get_all_channels():
    async with async_session() as s:
        res = await s.execute(select(Channel).order_by(Channel.id))
        return res.scalars().all()


async def delete_channel(channel_id) -> None:
    async with async_session() as s:
        await s.execute(delete(Channel).where(Channel.id == channel_id))
        await s.commit()


async def update_channel_count(channel_id, count: int) -> None:
    async with async_session() as s:
        await s.execute(update(Channel).where(Channel.id == channel_id).values(current_count=count))
        await s.commit()


async def deactivate_channel(channel_id) -> None:
    async with async_session() as s:
        await s.execute(update(Channel).where(Channel.id == channel_id).values(is_active=False))
        await s.commit()


# ═══════════════════════════════ PAYMENTS ════════════════════════════════════

async def create_payment(user_id, months, amount, method) -> Payment:
    async with async_session() as s:
        p = Payment(user_id=user_id, months=months, amount=amount, method=method)
        s.add(p)
        await s.commit()
        await s.refresh(p)
        return p


async def set_payment_receipt(payment_id, file_id) -> None:
    async with async_session() as s:
        await s.execute(update(Payment).where(Payment.id == payment_id).values(receipt_file_id=file_id))
        await s.commit()


async def get_payment(payment_id) -> Payment | None:
    async with async_session() as s:
        return await s.get(Payment, payment_id)


async def review_payment(payment_id, status, reviewed_by, reason=None) -> None:
    async with async_session() as s:
        await s.execute(
            update(Payment).where(Payment.id == payment_id)
            .values(status=status, reviewed_by=reviewed_by, reject_reason=reason, reviewed_at=datetime.utcnow())
        )
        await s.commit()


# ═══════════════════════════════ REFERRAL ════════════════════════════════════

async def add_referral(referrer_id, referred_id) -> bool:
    """Yangi referal qo'shadi (takror bo'lmasa). True = qo'shildi."""
    async with async_session() as s:
        res = await s.execute(select(Referral).where(Referral.referred_id == referred_id))
        if res.scalar_one_or_none():
            return False
        s.add(Referral(referrer_id=referrer_id, referred_id=referred_id))
        await s.commit()
        return True


async def count_referrals(referrer_id) -> int:
    async with async_session() as s:
        return (await s.execute(
            select(func.count(Referral.id)).where(Referral.referrer_id == referrer_id)
        )).scalar() or 0


async def count_unrewarded(referrer_id) -> int:
    async with async_session() as s:
        return (await s.execute(
            select(func.count(Referral.id)).where(
                Referral.referrer_id == referrer_id, Referral.is_rewarded == False)  # noqa: E712
        )).scalar() or 0


async def mark_referrals_rewarded(referrer_id, n: int) -> None:
    async with async_session() as s:
        res = await s.execute(
            select(Referral.id).where(
                Referral.referrer_id == referrer_id, Referral.is_rewarded == False  # noqa: E712
            ).limit(n)
        )
        ids = [r[0] for r in res.all()]
        if ids:
            await s.execute(update(Referral).where(Referral.id.in_(ids)).values(is_rewarded=True))
            await s.commit()


# ═══════════════════════════════ ADS ═════════════════════════════════════════

async def add_ad(data: dict) -> Advertisement:
    async with async_session() as s:
        ad = Advertisement(**data)
        s.add(ad)
        await s.commit()
        await s.refresh(ad)
        return ad


async def get_active_ads():
    now = datetime.utcnow()
    async with async_session() as s:
        res = await s.execute(select(Advertisement).where(Advertisement.is_active == True))  # noqa: E712
        ads = res.scalars().all()
        return [a for a in ads if (not a.start_at or a.start_at <= now) and (not a.end_at or a.end_at >= now)]


async def get_all_ads():
    async with async_session() as s:
        res = await s.execute(select(Advertisement).order_by(Advertisement.id.desc()))
        return res.scalars().all()


async def delete_ad(ad_id) -> None:
    async with async_session() as s:
        await s.execute(delete(Advertisement).where(Advertisement.id == ad_id))
        await s.commit()


# ═══════════════════════════════ ADMINS ══════════════════════════════════════

async def is_admin(user_id) -> bool:
    if user_id == settings.owner_id:
        return True
    async with async_session() as s:
        return (await s.get(Admin, user_id)) is not None


async def add_admin(user_id, role="moderator", added_by=None) -> None:
    async with async_session() as s:
        existing = await s.get(Admin, user_id)
        if existing:
            existing.role = role
        else:
            s.add(Admin(user_id=user_id, role=role, added_by=added_by))
        await s.commit()


async def remove_admin(user_id) -> None:
    async with async_session() as s:
        await s.execute(delete(Admin).where(Admin.user_id == user_id))
        await s.commit()


async def list_admins():
    async with async_session() as s:
        res = await s.execute(select(Admin))
        return res.scalars().all()


# ═══════════════════════════════ SETTINGS ════════════════════════════════════

async def get_setting(key, default=None):
    async with async_session() as s:
        st = await s.get(Setting, key)
        return st.value if st else default


async def set_setting(key, value) -> None:
    async with async_session() as s:
        st = await s.get(Setting, key)
        if st:
            st.value = value
        else:
            s.add(Setting(key=key, value=value))
        await s.commit()


# ═══════════════════════════════ LOGS ════════════════════════════════════════

async def add_log(action, actor_id=None, details=None) -> None:
    async with async_session() as s:
        s.add(Log(action=action, actor_id=actor_id, details=details))
        await s.commit()


async def get_logs(limit=20):
    async with async_session() as s:
        res = await s.execute(select(Log).order_by(Log.id.desc()).limit(limit))
        return res.scalars().all()


# ═══════════════════════════════ STATISTIKA ══════════════════════════════════

async def get_stats() -> dict:
    now = datetime.utcnow()
    today = now - timedelta(days=1)
    week = now - timedelta(days=7)
    async with async_session() as s:
        total = (await s.execute(select(func.count(User.user_id)))).scalar() or 0
        today_new = (await s.execute(select(func.count(User.user_id)).where(User.created_at >= today))).scalar() or 0
        active = (await s.execute(select(func.count(User.user_id)).where(User.last_active >= week))).scalar() or 0
        premium = (await s.execute(
            select(func.count(User.user_id)).where(User.is_premium == True, User.premium_until > now)  # noqa: E712
        )).scalar() or 0
        movies = (await s.execute(select(func.count(Movie.id)))).scalar() or 0
        views = (await s.execute(select(func.coalesce(func.sum(Movie.views), 0)))).scalar() or 0
        income = (await s.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status.in_(["approved", "paid"]))
        )).scalar() or 0
        return {
            "total": total, "today": today_new, "active": active,
            "premium": premium, "movies": movies, "views": views, "income": income,
        }
