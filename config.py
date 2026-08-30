
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")
CMC_API_KEY = os.getenv("CMC_API_KEY")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

# باقات الاشتراك (للعرض فقط)
SUBSCRIPTION_PLANS = {
    "1_month": {"days": 30, "price_usd": 20},
    "3_months": {"days": 90, "price_usd": 50},
    "6_months": {"days": 180, "price_usd": 90},
    "12_months": {"days": 365, "price_usd": 150},
}
