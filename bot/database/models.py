"""
Ma'lumotlar bazasi modellari (ER sxema).

Spec'dagi barcha jadvallar shu yerda. SQLite + SQLAlchemy 2.0.
Bog'lanishlar (relationships) keyingi bosqichlarda kerak bo'lganda qo'shiladi —
hozir sxema toza va tushunarli bo'lishi uchun asosan ustunlar berilgan.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.base import Base


class User(Base):
    """Foydalanuvchilar."""
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    lang: Mapped[str] = mapped_column(String(2), default="uz")

    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime)

    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_captcha_passed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Referal
    ref_code: Mapped[str | None] = mapped_column(String(16), unique=True)
    referred_by: Mapped[int | None] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_active: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Admin(Base):
    """Adminlar va rollari."""
    __tablename__ = "admins"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role: Mapped[str] = mapped_column(String(32), default="moderator")
    # rollar: super_admin | moderator | content_admin | ads_admin
    added_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Category(Base):
    """Kino kategoriyalari/janrlari."""
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)


class Movie(Base):
    """Kinolar."""
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    genre: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(64))
    year: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[str | None] = mapped_column(String(16))
    duration: Mapped[str | None] = mapped_column(String(32))
    quality: Mapped[str | None] = mapped_column(String(16))  # 4K / FullHD / HD

    file_id: Mapped[str | None] = mapped_column(Text)
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)  # faqat premium uchun

    views: Mapped[int] = mapped_column(Integer, default=0)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Channel(Base):
    """Majburiy obuna kanallari (maqsadli obunachi soni bilan)."""
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64))     # -100... yoki @username
    username: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(128))
    invite_link: Mapped[str | None] = mapped_column(String(255))

    target_count: Mapped[int] = mapped_column(Integer, default=0)   # maqsad (0 = cheksiz)
    current_count: Mapped[int] = mapped_column(Integer, default=0)  # oxirgi tekshiruvdagi son
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Payment(Base):
    """To'lovlar — karta+chek va avtomatik (Telegram Payments)."""
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    months: Mapped[int] = mapped_column(Integer)            # tarif: 1/3/6/12
    amount: Mapped[int] = mapped_column(Integer)            # so'mda
    method: Mapped[str] = mapped_column(String(16))         # card | telegram
    status: Mapped[str] = mapped_column(String(16), default="pending")
    # status: pending | approved | rejected | paid
    receipt_file_id: Mapped[str | None] = mapped_column(Text)  # chek rasmi (card uchun)
    reject_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)


class Advertisement(Base):
    """Reklama postlari (faqat oddiy foydalanuvchilarga ko'rsatiladi)."""
    __tablename__ = "advertisements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_type: Mapped[str] = mapped_column(String(16), default="text")  # text|photo|video
    text: Mapped[str | None] = mapped_column(Text)
    file_id: Mapped[str | None] = mapped_column(Text)
    button_text: Mapped[str | None] = mapped_column(String(64))
    button_url: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime)
    end_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Referral(Base):
    """Referal kelishlar."""
    __tablename__ = "referrals"
    __table_args__ = (UniqueConstraint("referred_id", name="uq_referred_once"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, index=True)
    referred_id: Mapped[int] = mapped_column(BigInteger)
    is_rewarded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Favorite(Base):
    """Sevimli kinolar / watchlist."""
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_user_movie_fav"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class History(Base):
    """Ko'rilgan kinolar tarixi."""
    __tablename__ = "history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Log(Base):
    """Tizim loglari (admin amallari, to'lovlar va h.k.)."""
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Setting(Base):
    """Kalit-qiymat sozlamalar (admin paneldan o'zgaradigan)."""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)
