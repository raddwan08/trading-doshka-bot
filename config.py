import os
from dotenv import load_dotenv

load_dotenv()


# Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN غير موجود في متغيرات البيئة"
    )


# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///crypto_bot.db"
)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )


# Wallets
WALLETS = {
    "SOL": os.getenv("SOL_WALLET"),
    "ETH": os.getenv("ETH_WALLET"),
    "BSC": os.getenv("BSC_WALLET")
}


# Subscription Plans
SUBSCRIPTION_PLANS = {
    "monthly": {
        "duration_days": 30,
        "price": 25,
        "name": "شهري"
    },

    "quarterly": {
        "duration_days": 90,
        "price": 60,
        "name": "3 أشهر"
    },

    "half_yearly": {
        "duration_days": 180,
        "price": 100,
        "name": "6 أشهر"
    },

    "yearly": {
        "duration_days": 365,
        "price": 180,
        "name": "سنوي"
    }
}


COINGECKO_API = "https://api.coingecko.com"
