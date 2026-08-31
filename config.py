
import os
from dotenv import load_dotenv

load_dotenv()

# إعدادات البوت
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# قاعدة البيانات (Railway سيضيف DATABASE_URL تلقائياً)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///crypto_bot.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# محافظ الدفع
WALLETS = {
    "SOL": os.getenv("SOL_WALLET", "5JSJzkF9GU6GA28J57xxBvSngoaHtbLGGwQkKHGUu1Dt"),
    "ETH": os.getenv("ETH_WALLET", "0xF79A1bEc46037dcA06077889F4bb1A111B67723e"),
    "BSC": os.getenv("BSC_WALLET", "0xF79A1bEc46037dcA06077889F4bb1A111B67723e")
}

# خطط الاشتراك
SUBSCRIPTION_PLANS = {
    "monthly": {"duration_days": 30, "price": 25, "name": "شهري"},
    "quarterly": {"duration_days": 90, "price": 60, "name": "3 أشهر"},
    "half_yearly": {"duration_days": 180, "price": 100, "name": "6 أشهر"},
    "yearly": {"duration_days": 365, "price": 180, "name": "سنوي"}
}

# إعدادات API
COINGECKO_API = "https://api.coingecko.com"
