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
    subscription_keyboard
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
        "❌ BOT_TOKEN غير موجود في Environment Variables"
    )


# =========================
# Database
# =========================

db = Database()


# =========================
# API
# =========================

crypto_api = CryptoAPI()


# =========================
# Analysis Handler
# =========================

analysis_handler = AnalysisHandler(
    db=db,
    crypto_api=crypto_api
)


# ==================================================
# START
# ==================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🚀 أهلاً بك في Doshka Trading Pro\n\n"
        "📊 التحليل والمدارس متاحة مجاناً.\n"
        "🚀 قسم Futures متاح للمشتركين.\n\n"
        "اختر الخدمة من القائمة:",

        reply_markup=main_menu_keyboard()
    )


# ==================================================
# ANALYSIS MENU
# ==================================================

async def analysis_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await analysis_handler.show_analysis_menu(
        update,
        context
    )


# ==================================================
# SUBSCRIBE COMMAND
# ==================================================

async def subscribe(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "💳 اشتراك Doshka Trading Pro\n\n"
        "🚀 الاشتراك يمنحك الوصول إلى قسم Futures "
        "والخدمات المدفوعة.\n\n"
        "اختر الباقة المناسبة:",

        reply_markup=subscription_keyboard()
    )


# ==================================================
# SUBSCRIPTION MENU BUTTON
# ==================================================

async def subscribe_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    await query.edit_message_text(

        "💳 اشتراك Doshka Trading Pro\n\n"
        "🚀 الاشتراك مطلوب لاستخدام Futures "
        "والخدمات المدفوعة.\n\n"
        "اختر الباقة:",

        reply_markup=subscription_keyboard()
    )


# ==================================================
# HELP
# ==================================================

async def help_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    await query.edit_message_text(

        "ℹ️ المساعدة\n\n"

        "📊 التحليل:\n"
        "اختر مدرسة التحليل ثم أرسل رمز العملة.\n\n"

        "مثال:\n"
        "BTC\n"
        "ETH\n"
        "SOL\n\n"

        "🚀 Futures:\n"
        "قسم مخصص للمشتركين.\n\n"

        "💳 الاشتراك:\n"
        "استخدم /subscribe أو زر الاشتراك.\n\n"

        "يمكنك العودة للقائمة باستخدام /start"
    )


# ==================================================
# FUTURES
# ==================================================

async def futures_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    user_id = update.effective_user.id


    # التحقق من الاشتراك
    if not db.check_subscription(user_id):

        await query.edit_message_text(

            "🔒 قسم Futures متاح للمشتركين فقط.\n\n"
            "💳 يمكنك الاشتراك باستخدام:\n"
            "/subscribe"

        )

        return


    await query.edit_message_text(

        "🚀 Futures Trading\n\n"
        "✅ تم التحقق من اشتراكك.\n\n"
        "سيتم هنا إضافة:\n"
        "📈 تحليل Futures\n"
        "🎯 إشارات الدخول\n"
        "🛑 وقف الخسارة\n"
        "💰 الأهداف\n"
        "⚖️ إدارة المخاطر"
    )


# ==================================================
# PRICES
# ==================================================

async def prices_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    await query.edit_message_text(

        "💰 الأسعار\n\n"
        "يمكنك استخدام الأمر:\n\n"
        "/price BTC\n"
        "/price ETH\n"
        "/price SOL"
    )


# ==================================================
# ALERTS
# ==================================================

async def alerts_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    await query.edit_message_text(

        "🔔 التنبيهات\n\n"
        "سيتم إضافة نظام التنبيهات هنا قريباً."
    )


# ==================================================
# SUBSCRIPTION PLAN
# ==================================================

async def select_subscription(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    plans = {
        "subscribe_1m": ("📅 اشتراك شهر", 20),
        "subscribe_3m": ("💎 اشتراك 3 أشهر", 50),
        "subscribe_6m": ("👑 اشتراك 6 أشهر", 75),
        "subscribe_1y": ("🏆 اشتراك سنة", 125),
    }

    plan = plans.get(query.data)

    if not plan:
        return

    plan_name, price = plan

    context.user_data["selected_plan"] = query.data
    context.user_data["selected_price"] = price

    await query.edit_message_text(
        f"{plan_name}\n\n"
        f"💰 السعر: {price} USDT\n\n"
        "اختر شبكة الدفع:",
        reply_markup=payment_network_keyboard()
        
    )# ==================================================
# PAYMENT
# ==================================================

async def payment_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    await query.edit_message_text(
        "💳 طرق الدفع:\n\n"
        "🟣 SOL:\n"
        "ضع محفظة SOL هنا\n\n"
        "🔵 ETH:\n"
        "ضع محفظة ETH هنا\n\n"
        "🟡 BNB:\n"
        "ضع محفظة BNB هنا\n\n"
        "بعد الدفع أرسل Transaction Hash"
    )


# 


# ==================================================
# BACK TO MAIN
# ==================================================

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


# ==================================================
# CANCEL
# ==================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()


    await update.message.reply_text(

        "❌ تم إلغاء العملية.",

        reply_markup=main_menu_keyboard()
    )


    return ConversationHandler.END


# ==================================================
# ERROR HANDLER
# ==================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.exception(
        "حدث خطأ أثناء معالجة التحديث:",
        exc_info=context.error
    )


# ==================================================
# MAIN
# ==================================================

def main():


    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )


    # ==============================================
    # Commands
    # ==============================================

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


    # ==============================================
    # Analysis Menu
    # ==============================================

    application.add_handler(

        CallbackQueryHandler(
            analysis_menu,
            pattern="^analysis_menu$"
        )

    )


    # ==============================================
    # Analysis Conversation
    # ==============================================

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


    # ==============================================
    # Subscription
    # ==============================================

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
# ==============================================
# Payment
# ==============================================

application.add_handler(
    CallbackQueryHandler(
        payment_menu,
        pattern="^payment_menu$"
    )
)
    )


    # ==============================================
    # Futures
    # ==============================================

    application.add_handler(

        CallbackQueryHandler(
            futures_menu,
            pattern="^futures_menu$"
        )

    )


    # ==============================================
    # Help
    # ==============================================

    application.add_handler(

        CallbackQueryHandler(
            help_menu,
            pattern="^help_menu$"
        )

    )


    # ==============================================
    # Prices
    # ==============================================

    application.add_handler(

        CallbackQueryHandler(
            prices_menu,
            pattern="^prices_menu$"
        )

    )


    # ==============================================
    # Alerts
    # ==============================================

    application.add_handler(

        CallbackQueryHandler(
            alerts_menu,
            pattern="^alerts_menu$"
        )

    )


    # ==============================================
    # Back
    # ==============================================

    application.add_handler(

        CallbackQueryHandler(
            back_main,
            pattern="^back_main$"
        )

    )


    # ==============================================
    # Errors
    # ==============================================

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
