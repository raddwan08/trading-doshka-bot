
import os
from dotenv import load_dotenv

load_dotenv()


# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Admin Telegram ID
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


# Database
DATABASE = "doshka.db"


# العملات الأساسية
COINS = [
    "BTC",
    "ETH",
    "BNB",
    "SOL",
    "XRP",
    "DOGE",
    "ADA",
    "AVAX"
]


# الفريمات
TIMEFRAMES = [
    "5m",
    "15m",
    "1h",
    "4h",
    "1d"
]


# المدارس
SCHOOLS = {

    "wyckoff": {
        "name": "📊 Wyckoff",
        "description":
        "تحليل التجميع والتصريف والسيولة والحجم"
    },

    "elliott": {
        "name": "🌊 Elliott Wave",
        "description":
        "تحليل الموجات والاتجاه"
    },

    "harmonic": {
        "name": "🦋 Harmonic",
        "description":
        "اكتشاف نماذج Gartley و Bat"
    },

    "classic": {
        "name": "📈 Classic Technical",
        "description":
        "RSI MACD EMA Support Resistance"
    },

    "whales": {
        "name": "🐋 Whales",
        "description":
        "كشف تحركات الحجم الكبيرة"
    }
}



# خطط الاشتراك

PLANS = {

    "basic": {
        "name": "Basic",
        "price": 15,
        "days": 30
    },

    "pro": {
        "name": "Professional",
        "price": 40,
        "days": 90
    },

    "vip": {
        "name": "VIP Futures",
        "price": 100,
        "days": 365
    }

}


# أنواع الحساب

MARKETS = {

    "spot": {
        "name": "Spot",
        "premium": False
    },

    "future": {
        "name": "Futures",
        "premium": True
    }

}


# مدة فحص التنبيهات
ALERT_INTERVAL = 60
