import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_bot.db")

# Payment Configuration
USDT_TRC20_WALLET = os.getenv("USDT_TRC20_WALLET")
BTC_WALLET = os.getenv("BTC_WALLET")
ETH_WALLET = os.getenv("ETH_WALLET")

SUBSCRIPTION_PLANS = {
    "1_month": {"days": 30, "price_usd": 20, "features": ["تحليل كامل", "جميع المدارس", "تنبيهات فورية"]},
    "3_months": {"days": 90, "price_usd": 50, "features": ["تحليل كامل", "جميع المدارس", "تنبيهات فورية", "أولوية في الدعم"]},
    "6_months": {"days": 180, "price_usd": 90, "features": ["تحليل كامل", "جميع المدارس", "تنبيهات فورية", "أولوية في الدعم", "تحليلات حصرية"]},
    "12_months": {"days": 365, "price_usd": 150, "features": ["تحليل كامل", "جميع المدارس", "تنبيهات فورية", "أولوية في الدعم", "تحليلات حصرية", "خصم خاص"]},
}

# API Configuration
COINGECKO_API = "https://api.coingecko.com/api/v3"
