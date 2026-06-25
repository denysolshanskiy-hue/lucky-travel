import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    mono_payment_url: str | None
    camping_payment_url: str | None
    supabase_url: str
    supabase_key: str


def load_config() -> Config:
    load_dotenv()

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is missing. Add it to .env")

    raw_admins = os.getenv("ADMIN_IDS", "").replace(" ", "")
    admin_ids = {int(item) for item in raw_admins.split(",") if item}
    if not admin_ids:
        raise RuntimeError("ADMIN_IDS is missing. Add your Telegram ID to .env")

    mono_payment_url = os.getenv("MONO_PAYMENT_URL", "").strip() or None
    camping_payment_url = (
        os.getenv("CAMPING_PAYMENT_URL", "").strip()
        or "https://send.monobank.ua/jar/49A7KYoxE3"
    )
    
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    if not supabase_url:
        raise RuntimeError("SUPABASE_URL is missing. Add it to .env")
    
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()
    if not supabase_key:
        raise RuntimeError("SUPABASE_KEY is missing. Add it to .env")

    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        mono_payment_url=mono_payment_url,
        camping_payment_url=camping_payment_url,
        supabase_url=supabase_url,
        supabase_key=supabase_key,
    )
