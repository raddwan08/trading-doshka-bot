import asyncio
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

from config import BOT_TOKEN
from market.binance import get_price, get_market_status
from database import add_user, is_subscriber
from chart import create_chart


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    add_user(
        user.id,
        user.username
    )

    keyboard = [

        [
            InlineKeyboardButton(
                "📊 التحليل الفني",
                callback_data="analysis"
            )
        ],

        [
            InlineKeyboardButton(
                "💎 Spot",
                callback_data="spot"
            ),

            InlineKeyboardButton(
                "💎 Futures",
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
                "💳 الاشتراك",
                callback_data="subscribe"
            )
        ]

    ]


    await update.message.reply_text(
        """
🤖 Crypto Analyzing Bot

اختر الخدمة:
        """,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )



# =========================
# BUTTONS
# =========================

async def buttons(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):


    query = update.callback_query

    await query.answer()


    data = query.data



    # تحليل

    if data == "analysis":

        await query.edit_message_text(

        """
📊 التحليل الفني

اختر العملة:

BTC
ETH
SOL
BNB

سيتم إنشاء شارت مستقل مع المؤشرات.
        """

        )



    # Spot

    elif data == "spot":

        if not is_subscriber(query.from_user.id):

            await query.edit_message_text(
            """
💎 Spot Trading

هذه الخدمة للمشتركين فقط.

تشمل:
✅ إشارات دخول
✅ إشارات خروج
✅ متابعة العقود
✅ تنبيهات السوق
            """
            )

            return


        await query.edit_message_text(

        """
💎 Spot فعال

جاري مراقبة السوق...

سيصلك إشعار عند:
🟢 دخول
🔴 خروج
⚠️ تغير مهم
        """

        )



    # Futures

    elif data == "futures":

        if not is_subscriber(query.from_user.id):

            await query.edit_message_text(

            """
💎 Futures

خدمة مدفوعة.

تشمل:
⚡ Long
⚡ Short
⚡ Stop Loss
⚡ تعديل العقود
⚡ تنبيهات الانحراف

            """

            )

            return



        await query.edit_message_text(

        """
💎 Futures فعال

المراقبة تعمل.
        """

        )



    # Alerts


    elif data == "alerts":


        await query.edit_message_text(

        """
🔔 التنبيهات

سيتم إرسال:

🟢 دخول صفقة
🔴 خروج
📈 تغير اتجاه
⚠️ خلل Binance
📢 تعديل عقد

        """

        )



    # Subscribe


    elif data == "subscribe":

        await query.edit_message_text(

        """
💳 الاشتراك

اختر الباقة المناسبة.

سيتم تفعيل:
Spot + Futures
والتنبيهات المباشرة.
        """

        )





# =========================
# PRICE COMMAND
# =========================


async def price(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):


    coin = "BTCUSDT"


    data = await get_price(
        coin
    )


    await update.message.reply_text(

    f"""
💰 {coin}

السعر:
{data}

    """

    )





# =========================
# MARKET
# =========================


async def market(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):


    status = await get_market_status()


    await update.message.reply_text(

    status

    )





# =========================
# RUN BOT
# =========================


def main():

    app = Application.builder().token(
        BOT_TOKEN
    ).build()


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(
        CommandHandler(
            "price",
            price
        )
    )


    app.add_handler(
        CommandHandler(
            "market",
            market
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            buttons
        )
    )


    print(
        "BOT STARTED"
    )


    app.run_polling()



if __name__ == "__main__":

    main()
