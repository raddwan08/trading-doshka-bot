# config.py

import os
from dataclasses import dataclass


# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


# Database
DB_NAME = "trading_bot.db"


# Binance
BINANCE_API = "https://api.binance.com"


# العملات التي يراقبها النظام
COINS = [
    "BTC",
    "ETH",
    "BNB",
    "SOL",
    "XRP",
    "ADA",
    "DOGE"
]


# الفواصل الزمنية
TIMEFRAMES = [
    "5m",
    "15m",
    "1h",
    "4h",
    "1d"
]


@dataclass
class Plan:
    name: str
    price: float
    spot: bool
    futures: bool
    alerts: bool


# الاشتراكات
PLANS = {

    "free": Plan(
        name="تجريبي",
        price=0,
        spot=False,
        futures=False,
        alerts=False
    ),

    "pro": Plan(
        name="PRO Spot",
        price=20,
        spot=True,
        futures=False,
        alerts=True
    ),

    "elite": Plan(
        name="ELITE Futures",
        price=50,
        spot=True,
        futures=True,
        alerts=True
    )
}


# المدارس
SCHOOLS = {

    "wyckoff": {
        "name": "وايكوف",
        "emoji": "📊"
    },

    "elliott": {
        "name": "إليوت",
        "emoji": "🌊"
    },

    "harmonic": {
        "name": "هارمونيك",
        "emoji": "🦋"
    },

    "classic": {
        "name": "كلاسيكي",
        "emoji": "📈"
    },

    "whales": {
        "name": "الحيتان",
        "emoji": "🐋"
    }
}


# إعدادات التنبيهات

ALERT_INTERVAL = 60


# العملات التي تتم مراقبتها للعقود

FUTURES_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT"
]


# حدود تنبيه الحيتان

WHALE_VOLUME_MULTIPLIER = 3
