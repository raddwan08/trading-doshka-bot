# main.py

import os
import logging


from telegram import Update


from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters
)



from handlers.analysis_handler import (
    AnalysisHandler,
    WAITING_SYMBOL
)



from services.crypto_api import CryptoAPI

from services.payment import PaymentService
from services.futures_service import FuturesService

from database.db import Database



from utils.keyboards import (
    main_menu_keyboard,
    subscription_keyboard
)



# =========================
# Logging
# =========================


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    )
)


logger = logging.getLogger(__name__)



# =========================
# Token
# =========================


BOT_TOKEN = os.getenv(
    "BOT_TOKEN"
)


if not BOT_TOKEN:

    raise RuntimeError(
        "BOT_TOKEN missing"
    )



# =========================
# Database
# =========================


db = Database()



# =========================
# APIs
# =========================


crypto_api = CryptoAPI()

#=========================
# Futures Service
# =========================

futures_service = FuturesService(

    db=db,

    crypto_api=crypto_api

)



# =========================
# Payment
# =========================


payment_service = PaymentService(
    db
)



# =========================
# Analysis
# =========================


analysis_handler = AnalysisHandler(
    db=db,
    crypto_api=crypto_api
)





# =========================
# START
# =========================


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):


    await update.message.reply_text(

        "🚀 أهلاً بك في Doshka Trading Pro\n\n"
        "📊 التحليل متاح.\n"
        "💳 الاشتراك والدفع التلقائي متاح.\n\n"
        "اختر الخدمة:",

        reply_markup=main_menu_keyboard()

    )
  # =========================
# ANALYSIS MENU
# =========================


async def analysis_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await analysis_handler.show_analysis_menu(
        update,
        context
    )



# =========================
# SUBSCRIBE
# =========================


async def subscribe(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):


    await update.message.reply_text(

        "💳 اشتراك Doshka Trading Pro\n\n"
        "اختر الباقة:",

        reply_markup=subscription_keyboard()

    )



# =========================
# SUBSCRIBE BUTTON
# =========================


async def subscribe_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):


    query = update.callback_query


    await query.answer()



    await query.edit_message_text(

        "💳 اختر خطة الاشتراك:",

        reply_markup=subscription_keyboard()

    )



# =========================
# SELECT SUBSCRIPTION
# =========================


async def select_subscription(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):


    query = update.callback_query


    await query.answer()



    plans = {


        "subscribe_1m":
        (
            "📅 شهر",
            20
        ),


        "subscribe_3m":
        (
            "💎 3 أشهر",
            50
        ),


        "subscribe_6m":
        (
            "👑 6 أشهر",
            75
        ),


        "subscribe_1y":
        (
            "🏆 سنة",
            125
        )

    }



    data = query.data



    plan = plans.get(
        data
    )



    if not plan:

        return



    name, amount = plan



    user_id = (
        update.effective_user.id
    )


    username = (
        update.effective_user.username
        or "unknown"
    )



    # إنشاء طلب دفع

    payment_id = db.create_payment(

        user_id,

        username,

        data,

        amount,

        "USDT",

        os.getenv(
            "TRON_WALLET"
        )

    )



    await query.edit_message_text(

        f"{name}\n\n"

        f"💰 السعر: {amount} USDT\n\n"

        "🟢 شبكة الدفع:\n"
        "USDT TRC20\n\n"

        "💳 المحفظة:\n"

        f"{os.getenv('TRON_WALLET')}\n\n"

        "✅ بعد الدفع لا ترسل أي Hash.\n"
        "سيتم التحقق تلقائياً من البلوكشين.\n\n"

        f"رقم الطلب: {payment_id}"

    )



# =========================
# FUTURES
# =========================


async def futures_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = update.effective_user.id

    admin_id = int(
        os.getenv("ADMIN_ID")
    )


    # المؤسس لديه صلاحية مجانية دائماً
    if user_id == admin_id:

        await query.edit_message_text(

            "👑 Founder Access\n\n"
            "🚀 Futures Trading\n\n"
            "✅ لديك وصول مجاني كمؤسس البوت."

        )

        return


    # المستخدمون الآخرون يحتاجون اشتراكاً
    if not db.check_subscription(
        user_id
    ):

        await query.edit_message_text(

            "🔒 Futures للمشتركين فقط.\n\n"
            "استخدم زر الاشتراك."

        )

        return


    await query.edit_message_text(

        "🚀 Futures Trading\n\n"
        "✅ الاشتراك فعال.\n\n"
        "سيتم إضافة إشارات Futures هنا."

    )


# =========================
# PRICES
# =========================


async def prices_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    await query.edit_message_text(

        "💰 الأسعار\n\n"
        "/price BTC\n"
        "/price ETH\n"
        "/price SOL"

    )



# =========================
# ALERTS
# =========================


async def alerts_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):


    query = update.callback_query


    await query.answer()



    await query.edit_message_text(

        "🔔 التنبيهات\n\n"
        "سيتم ربطها لاحقاً."

    )



# =========================
# HELP
# =========================


async def help_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):


    query = update.callback_query


    await query.answer()



    await query.edit_message_text(

        "ℹ️ المساعدة\n\n"
        "📊 التحليل:\n"
        "اختر المدرسة ثم أرسل العملة.\n\n"
        "💳 الدفع يتم تلقائياً."

    )
  # =========================
# BACK MAIN
# =========================


async def back_main(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    context.user_data.clear()


    await query.edit_message_text(

        "🏠 القائمة الرئيسية\n\n"
        "اختر الخدمة:",

        reply_markup=main_menu_keyboard()

    )



# =========================
# CANCEL
# =========================


async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):


    context.user_data.clear()


    if update.message:

        await update.message.reply_text(

            "❌ تم الإلغاء.",

            reply_markup=main_menu_keyboard()

        )


    return ConversationHandler.END



# =========================
# ERROR
# =========================


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.exception(
        "Bot Error",
        exc_info=context.error
    )



# =========================
# MAIN
# =========================


def main():


    application = (

        Application

        .builder()

        .token(BOT_TOKEN)

        .build()

    )



    # =====================
    # Commands
    # =====================


    application.add_handler(

        CommandHandler(
            "start",
            start
        )

    )


    application.add_handler(

        CommandHandler(
            "subscribe",
            subscribe
        )

    )


    application.add_handler(

        CommandHandler(
            "cancel",
            cancel
        )

    )



    # =====================
    # Analysis
    # =====================


    application.add_handler(

        CallbackQueryHandler(

            analysis_menu,

            pattern="^analysis_menu$"

        )

    )



    analysis_conversation = ConversationHandler(

        entry_points=[

            CallbackQueryHandler(

                analysis_handler.handle_analysis_callback,

                pattern=(
                    "^analysis_"
                    "(wyckoff|harmonic|classic|whales|tvl)$"
                )

            )

        ],


        states={

            WAITING_SYMBOL:[

                MessageHandler(

                    filters.TEXT
                    &
                    ~filters.COMMAND,

                    analysis_handler.receive_symbol

                )

            ]

        },


        fallbacks=[

            CommandHandler(
                "cancel",
                cancel
            )

        ],


        allow_reentry=True

    )



    application.add_handler(

        analysis_conversation

    )



    # =====================
    # Subscription
    # =====================


    application.add_handler(

        CallbackQueryHandler(

            subscribe_menu,

            pattern="^subscribe_menu$"

        )

    )



    application.add_handler(

        CallbackQueryHandler(

            select_subscription,

            pattern=(
                "^subscribe_"
                "(1m|3m|6m|1y)$"
            )

        )

    )



    # =====================
    # Futures
    # =====================


    application.add_handler(

        CallbackQueryHandler(

            futures_menu,

            pattern="^futures_menu$"

        )

    )



    # =====================
    # Other Buttons
    # =====================


    application.add_handler(

        CallbackQueryHandler(

            prices_menu,

            pattern="^prices_menu$"

        )

    )


    application.add_handler(

        CallbackQueryHandler(

            alerts_menu,

            pattern="^alerts_menu$"

        )

    )


    application.add_handler(

        CallbackQueryHandler(

            help_menu,

            pattern="^help_menu$"

        )

    )


    application.add_handler(

        CallbackQueryHandler(

            back_main,

            pattern="^back_main$"

        )

    )



    # =====================
    # Payment Monitor
    # =====================

    application.job_queue.run_repeating(

        payment_service.check_payments,

        interval=60,

        first=10

    )


    # =====================
    # Futures Signals
    # =====================

    application.job_queue.run_repeating(

        futures_service.send_signals,

        interval=3600,

        first=10

    )


    # =====================
    # Error Handler
    # =====================

    application.add_error_handler(

        error_handler

    )


    logger.info(

        "🚀 Doshka Trading Pro Started"

    )


    application.run_polling(

        drop_pending_updates=True

    )



if __name__ == "__main__":

    main()
