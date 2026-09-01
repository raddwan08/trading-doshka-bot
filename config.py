import os
from dotenv import load_dotenv

# ==========================================
# تحميل متغيرات البيئة
# ==========================================

load_dotenv()


# ==========================================
# Telegram Bot
# ==========================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN غير موجود في متغيرات البيئة"
    )


# ==========================================
# Database
# ==========================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///crypto_bot.db"
).strip()

# دعم PostgreSQL في Railway
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )


# ==========================================
# Wallets
# ==========================================

WALLETS = {
    "SOL": os.getenv("SOL_WALLET", "").strip(),
    "ETH": os.getenv("ETH_WALLET", "").strip(),
    "BSC": os.getenv("BSC_WALLET", "").strip()
}


# ==========================================
# Subscription Plans
# ==========================================

SUBSCRIPTION_PLANS = {
    "monthly": {
        "duration_days": 30,
        "price": 25.0,
        "name": "شهري"
    },

    "quarterly": {
        "duration_days": 90,
        "price": 60.0,
        "name": "3 أشهر"
    },

    "half_yearly": {
        "duration_days": 180,
        "price": 100.0,
        "name": "6 أشهر"
    },

    "yearly": {
        "duration_days": 365,
        "price": 180.0,
        "name": "سنوي"
    }
}


# ==========================================
# Blockchain RPC URLs
# ==========================================

ETH_RPC_URL = os.getenv(
    "ETH_RPC_URL",
    ""
).strip()

BSC_RPC_URL = os.getenv(
    "BSC_RPC_URL",
    ""
).strip()

SOL_RPC_URL = os.getenv(
    "SOL_RPC_URL",
    ""
).strip()


# ==========================================
# Solana USDT
# ==========================================

SOL_USDT_MINT = os.getenv(
    "SOL_USDT_MINT",
    ""
).strip()


# ==========================================
# Blockchain Settings
# ==========================================

EVM_LOOKBACK_BLOCKS = int(
    os.getenv(
        "EVM_LOOKBACK_BLOCKS",
        "500"
    )
)

PAYMENT_TOLERANCE = float(
    os.getenv(
        "PAYMENT_TOLERANCE",
        "0.000001"
    )
)


# ==========================================
# Crypto API
# ==========================================

COINGECKO_API = os.getenv(
    "COINGECKO_API",
    "https://api.coingecko.com/api/v3"
).strip()
