"""SQLAlchemy asosiy obyektlari: engine, session faktori va Base klassi."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

# SQLite uchun async engine (aiosqlite drayveri orqali)
engine = create_async_engine(settings.db_url, echo=False)

# Har bir so'rov uchun yangi sessiya yaratuvchi factory
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Barcha modellar uchun bazaviy klass."""
    pass


async def init_models() -> None:
    """Jadvallarni yaratadi (agar mavjud bo'lmasa). Bot ishga tushganda chaqiriladi."""
    # Modellar Base.metadata ga ro'yxatdan o'tishi uchun import qilinadi
    from bot.database import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
