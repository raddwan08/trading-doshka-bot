import os

# ضع توكن البوت هنا أو في Railway Variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")

# قاعدة البيانات
DATABASE = "users.db"


# العملات المتاحة
COINS = [
    "BTC",
    "ETH",
    "BNB",
    "SOL",
    "XRP",
    "ADA",
    "DOGE"
]


# المدارس التحليلية
SCHOOLS = {
    "classic": {
        "name": "📈 التحليل الكلاسيكي",
        "description": "EMA + RSI + MACD + اتجاه السوق"
    },

    "elliott": {
        "name": "🌊 موجات إليوت",
        "description": "تحليل الموجات والقمم والقيعان"
    },

    "wyckoff": {
        "name": "📊 وايكوف",
        "description": "تجميع وتوزيع وحركة الحجم"
    },

    "harmonic": {
        "name": "🦋 هارمونيك",
        "description": "نماذج XABCD ونسب فيبوناتشي"
    },

    "whales": {
        "name": "🐋 الحيتان",
        "description": "كشف الشموع ذات الحجم الكبير"
    },

    "liquidity": {
        "name": "🔒 السيولة",
        "description": "مناطق ضغط الشراء والبيع"
    }
}


# مدة التجربة
FREE_DAYS = 7
