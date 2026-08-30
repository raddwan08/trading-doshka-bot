import os
import logging
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

from market.binance import (
    get_price,
    get_futures_price,
    get_market_data
)

from market.signals import analyze_market

from database import (
    add_user,
    get_user_status
)


load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")


logging.basicConfig(
    level=logging.INFO
)



# =====================
# لوحة التحكم الرئيسية
# =====================

def main_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "📊 تحليل العملة",
                callback_data="analysis"
            )
        ],

        [
            InlineKeyboardButton(
                "⚡ Spot",
                callback_data="spot"
            ),
            InlineKeyboardButton(
                "🔥 Futures",
                callback_data="futures"
            )
        ],

        [
            InlineKeyboardButton(
                "🔔 التنبيهات",
                callback_data="alerts"
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
        ]

    ]

    return InlineKeyboardMarkup(keyboard)



# =====================
# START
# =====================

async def start(update: Update, context):

    user = update.effective_user

    add_user(
        user.id,
        user.username
    )


    await update.message.reply_text(

        """
🤖 Trading Doshka AI

نظام تحليل العملات الرقمية

يدعم:

✅ Spot
✅ Futures
✅ RSI
✅ EMA
✅ MACD
✅ دعم ومقاومة
✅ إشارات دخول وخروج


اكتب:

/analyze BTCUSDT

لتحليل أي عملة
        """,

        reply_markup=main_keyboard()

    )



# =====================
# تحليل العملة
# =====================

async def analyze(update: Update, context):


    symbol = "BTCUSDT"


    if context.args:

        symbol = context.args[0].upper()



    result = analyze_market(symbol)



    await update.message.reply_text(

        f"""
📊 تحليل {symbol}


💰 السعر:
{result['price']}


📈 الاتجاه:
{result['trend']}


🎯 الإشارة:
{result['signal']}


💪 القوة:
{result['strength']}%


📌 الدعم:
{result['support']}


🚧 المقاومة:
{result['resistance']}


⚡ السوق:
{result['market']}

        """

    )



# =====================
# Futures
# =====================

async def futures(update: Update, context):


    symbol = "BTCUSDT"


    if context.args:

        symbol = context.args[0].upper()



    price = get_futures_price(symbol)



    await update.message.reply_text(

        f"""
🔥 Futures

العملة:
{symbol}


السعر:
{price}

انتظار تحليل العقود...
        """

    )



# =====================
# Spot
# =====================

async def spot(update: Update, context):


    symbol = "BTCUSDT"


    if context.args:

        symbol=context.args[0].upper()



    price=get_price(symbol)



    await update.message.reply_text(

        f"""
💎 Spot

{symbol}

السعر:
{price}
        """

    )



# =====================
# الأزرار
# =====================

async def buttons(update:Update, context):


    query=update.callback_query

    await query.answer()



    if query.data=="analysis":

        await query.edit_message_text(

            "اكتب:\n/analyze BTCUSDT"

        )


    elif query.data=="spot":

        await query.edit_message_text(

            "اكتب:\n/spot ETHUSDT"

        )


    elif query.data=="futures":

        await query.edit_message_text(

            "اكتب:\n/futures BTCUSDT"

        )


    elif query.data=="subscribe":

        await query.edit_message_text(

            """
💎 Premium

سيتم تفعيل:

✅ Futures Alerts
✅ دخول وخروج
✅ إشارات قوية
✅ تنبيهات مباشرة
            """

        )


    elif query.data=="status":

        status=get_user_status(
            query.from_user.id
        )

        await query.edit_message_text(
            status
        )


    elif query.data=="alerts":

        await query.edit_message_text(

            "🔔 نظام التنبيهات Premium"

        )



# =====================
# تشغيل البوت
# =====================

def main():


    app=Application.builder().token(
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
        CommandHandler(
            "spot",
            spot
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            buttons
        )
    )



    print(
        "Trading Doshka AI Started"
    )



    app.run_polling()



if __name__=="__main__":

    main()
