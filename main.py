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
from database.db import Database


from utils.keyboards import (
    main_menu_keyboard,
    subscription_keyboard,
    payment_network_keyboard
)


# =========================
# Logging
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# =========================
# Environment
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود"
    )


# =========================
# Services
# =========================

db = Database()

crypto_api = CryptoAPI()


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
        "📊 تحليل العملات والمدارس متاح.\n"
        "🚀 Futures للمشتركين.\n\n"
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


async def subscribe_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    await query.edit_message_text(

        "💳 اشتراك Doshka Trading Pro\n\n"
        "اختر الباقة:",

        reply_markup=subscription_keyboard()
    )
  # =========================
# SELECT SUBSCRIPTION PLAN
# =========================

async def select_subscription(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    plans = {

        "subscribe_1m": "📅 اشتراك شهر - $20",
        "subscribe_3m": "💎 اشتراك 3 أشهر - $50",
        "subscribe_6m": "👑 اشتراك 6 أشهر - $75",
        "subscribe_1y": "🏆 اشتراك سنة - $125"

    }


    plan = plans.get(query.data)


    if not plan:
        return


    context.user_data["selected_plan"] = query.data


    await query.edit_message_text(

        f"{plan}\n\n"
        "💳 اختر شبكة الدفع:",

        reply_markup=payment_network_keyboard()
    )



# =========================
# PAYMENT NETWORK
# =========================

async def payment_network(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    wallets = {

        "payment_sol":
            (
                "🟣 SOL Network\n\n"
                f"Wallet:\n{os.getenv('SOL_WALLET')}"
            ),

        "payment_eth":
            (
                "🔵 Ethereum Network\n\n"
                f"Wallet:\n{os.getenv('ETH_WALLET')}"
            ),

        "payment_bnb":
            (
                "🟡 BNB Smart Chain\n\n"
                f"Wallet:\n{os.getenv('BNB_WALLET')}"
            )

    }


    wallet = wallets.get(query.data)


    if not wallet:
        return


    await query.edit_message_text(

        wallet +

        "\n\n"
        "بعد الدفع أرسل Transaction Hash للتحقق."

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


    if not db.check_subscription(user_id):

        await query.edit_message_text(

            "🔒 Futures للمشتركين فقط.\n\n"
            "استخدم زر الاشتراك."

        )

        return



    await query.edit_message_text(

        "🚀 Futures Trading\n\n"
        "✅ اشتراك فعال\n\n"
        "سيتم إضافة:\n"
        "📈 إشارات الدخول\n"
        "🎯 الأهداف\n"
        "🛑 وقف الخسارة\n"
        "⚖️ إدارة المخاطر"

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
        "استخدم:\n\n"
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
        "سيتم تفعيل نظام التنبيهات لاحقاً."

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
        "مثال:\n"
        "BTC\n"
        "ETH\n"
        "SOL"

    )



# =========================
# BACK
# =========================

async def back_main(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    context.user_data.clear()


    await query.edit_message_text(

        "🏠 القائمة الرئيسية",

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

    await update.message.reply_text(
        "❌ تم الإلغاء.",
        reply_markup=main_menu_keyboard()
    )

    return ConversationHandler.END



# =========================
# ERROR HANDLER
# =========================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.exception(
        "Error:",
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
    # Analysis Menu
    # =====================

    application.add_handler(

        CallbackQueryHandler(
            analysis_menu,
            pattern="^analysis_menu$"
        )

    )



    # =====================
    # Analysis Conversation
    # =====================

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

            WAITING_SYMBOL: [

                MessageHandler(

                    filters.TEXT
                    & ~filters.COMMAND,

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
            pattern="^subscribe_(1m|3m|6m|1y)$"
        )

    )


    # =====================
    # Payment
    # =====================

    application.add_handler(

        CallbackQueryHandler(
            payment_network,
            pattern="^payment_(sol|eth|bnb)$"
        )

    )



    # =====================
    # Other Menus
    # =====================

    application.add_handler(

        CallbackQueryHandler(
            futures_menu,
            pattern="^futures_menu$"
        )

    )


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
    # Errors
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
