import os
import logging
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

from market.binance import (
    get_price,
    get_market_data,
    get_futures_price
)

load_dotenv()

# Telegram Token
TOKEN = os.getenv("TELEGRAM_TOKEN")


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


# ======================
# START
# ======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton(
                "📊 التحليل الفني",
                callback_data="analysis"
            )
        ],
        [
            InlineKeyboardButton(
                "💎 الاشتراك",
                callback_data="subscribe"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 حالتي",
                callback_data="status"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ المساعدة",
                callback_data="help"
            )
        ]
    ]

    reply = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        """
🤖 Trading Doshka Bot

بوت تحليل العملات الرقمية

الأوامر:

/analyze - تحليل BTC
/futures - سعر العقود
/help - المساعدة
        """,
        reply_markup=reply
    )


# ======================
# HELP
# ======================

async def help_command(update: Update, context):

    await update.message.reply_text(
        """
📌 الأوامر:

/start
بدء البوت

/analyze
تحليل السوق

/futures
أسعار Futures

/help
المساعدة
"""
    )


# ======================
# ANALYSIS
# ======================

async def analyze(update: Update, context):

    symbol = "BTC/USDT"

    price = get_price(symbol)

    candles = get_market_data(
        symbol,
        "1h",
        50
    )

    if not price:

        await update.message.reply_text(
            "❌ تعذر جلب بيانات Binance"
        )
        return


    signal = "🟢 مراقبة شراء" if len(candles) > 0 else "⚪ لا توجد إشارة"


    await update.message.reply_text(
        f"""
📊 تحليل {symbol}

💰 السعر:
{price}

📈 الحالة:
{signal}

⏱ الإطار:
1H
"""
    )


# ======================
# FUTURES
# ======================

async def futures(update: Update, context):

    price = get_futures_price(
        "BTC/USDT"
    )

    await update.message.reply_text(
        f"""
⚡ Binance Futures

BTC/USDT

السعر:
{price}
"""
    )


# ======================
# BUTTONS
# ======================

async def buttons(update: Update, context):

    query = update.callback_query

    await query.answer()


    if query.data == "analysis":

        price = get_price()

        await query.edit_message_text(
            f"""
📊 التحليل

BTC/USDT

السعر:
{price}

الحالة:
🟢 مراقبة
"""
        )


    elif query.data == "help":

        await query.edit_message_text(
            "استخدم /analyze للتحليل"
        )


    elif query.data == "subscribe":

        await query.edit_message_text(
            "💎 الاشتراك قريباً"
        )


    elif query.data == "status":

        await query.edit_message_text(
            "📋 حسابك مجاني"
        )



# ======================
# MAIN
# ======================

def main():

    if not TOKEN:

        print(
            "ERROR: TELEGRAM_TOKEN missing"
        )
        return


    app = Application.builder().token(
        TOKEN
    ).build()


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )


    app.add_handler(
        CommandHandler(
            "analyze",
            analyze
        )
    )


    app.add_handler(
        CommandHandler(
            "futures",
            futures
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            buttons
        )
    )


    print(
        "Bot Started"
    )


    app.run_polling()



if __name__ == "__main__":
    main()
