"""
Markaziy konfiguratsiya.

MUHIM: Bu yerda hech qanday token yoki maxfiy ma'lumot YOZILMAGAN.
Barcha qiymatlar muhit o'zgaruvchilaridan (.env yoki BotHost Environment Variables)
o'qiladi. Shu tufayli kod ochiq GitHub'da turishi xavfsiz.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int = 0) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw.isdigit() else default


# BotHost konteynerida doimiy saqlanadigan papka (Dockerfile dan: ENV DATA_DIR=/app/data).
# Lokalda ishlatilganda ./data ishlatiladi.
DATA_DIR = os.getenv("DATA_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "").strip()
    owner_id: int = _get_int("OWNER_ID")
    bot_username: str = os.getenv("BOT_USERNAME", "").lstrip("@").strip()

    payment_provider_token: str = os.getenv("PAYMENT_PROVIDER_TOKEN", "").strip()

    # Premium tariflar: {oylar soni: narx}
    prices: dict[int, int] = field(default_factory=lambda: {
        1: _get_int("PRICE_1_MONTH", 15000),
        3: _get_int("PRICE_3_MONTH", 39000),
        6: _get_int("PRICE_6_MONTH", 69000),
        12: _get_int("PRICE_12_MONTH", 119000),
    })

    card_number: str = os.getenv("CARD_NUMBER", "").strip()
    card_holder: str = os.getenv("CARD_HOLDER", "").strip()

    referrals_per_reward: int = _get_int("REFERRALS_PER_REWARD", 5)
    reward_days: int = _get_int("REWARD_DAYS", 3)

    throttle_rate: float = float(os.getenv("THROTTLE_RATE", "0.7") or 0.7)

    # SQLite fayli doimiy papkada
    db_path: str = os.path.join(DATA_DIR, "cinema.db")

    @property
    def db_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_path}"

    def validate(self) -> None:
        """Ishga tushishdan oldin majburiy qiymatlarni tekshiradi."""
        missing = []
        if not self.bot_token:
            missing.append("BOT_TOKEN")
        if not self.owner_id:
            missing.append("OWNER_ID")
        if missing:
            raise RuntimeError(
                "Quyidagi muhit o'zgaruvchilari o'rnatilmagan: "
                + ", ".join(missing)
                + ". BotHost panelidagi Environment Variables bo'limiga qo'shing."
            )


settings = Settings()
