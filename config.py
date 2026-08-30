import os


# ==========================
# Telegram Bot
# ==========================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "PUT_YOUR_BOT_TOKEN_HERE"
)



# ==========================
# Admin
# ==========================

ADMIN_ID = int(
    os.getenv(
        "ADMIN_ID",
        "0"
    )
)



# ==========================
# Market Settings
# ==========================

DEFAULT_COIN = "BTC"

TIMEFRAMES = [

    "5m",
    "15m",
    "1h",
    "4h",
    "1D"

]


MARKETS = {

    "spot":
        "Spot",

    "futures":
        "Futures"

}



# ==========================
# Analysis Schools
# ==========================

SCHOOLS = {

    "wyckoff":
    {
        "name":"Wyckoff",
        "emoji":"📊"
    },


    "elliott":
    {
        "name":"Elliott Wave",
        "emoji":"🌊"
    },


    "harmonic":
    {
        "name":"Harmonic",
        "emoji":"🦋"
    },


    "classic":
    {
        "name":"Classic",
        "emoji":"📈"
    },


    "whales":
    {
        "name":"Whales",
        "emoji":"🐋"
    }

}



# ==========================
# Subscription Placeholder
# ==========================

PLANS = {

    "trial":
    {
        "name":"Trial",
        "days":7
    },


    "premium":
    {
        "name":"Premium",
        "days":30
    }

}



# ==========================
# Database
# ==========================

DATABASE = "doshka.db"
