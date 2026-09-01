import os
import logging

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from handlers.analysis_handler import AnalysisHandler
from services.crypto_api import CryptoAPI
from database.db import Database

from utils.keyboards import main_menu_keyboard


# =========================
# Logging
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# =========================
# Bot Token
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")


if not BOT_TOKEN:
    raise Exception(
        "BOT_TOKEN غير موجود في Environment Variables"
    )


# =========================
# Database
# =========================

db = Database()


# =========================
# API Services
# =========================

crypto_api = CryptoAPI()


# =========================
# Handlers
# =========================

analysis_handler = AnalysisHandler(
    db=db,
    crypto_api=crypto_api
)


# =========================
# Commands
# =========================

async def start(
    update,
    context
):

    await update.message.reply_text(

        "🚀 أهلاً بك في Doshka Trading Pro\n\n"
        "اختر الخدمة من القائمة:",

        reply_markup=main_menu_keyboard()

    )



async def analysis_menu(
    update,
    context
):

    await analysis_handler.show_analysis_menu(
        update,
        context
    )



# =========================
# Error Handler
# =========================

async def error_handler(
    update,
    context
):

    logger.error(
        f"Error: {context.error}"
    )



# =========================
# Run Bot
# =========================

def main():


    application = (

        Application
        .builder()
        .token(BOT_TOKEN)
        .build()

    )



    # /start

    application.add_handler(

        CommandHandler(
            "start",
            start
        )

    )



    # زر التحليل الرئيسي

    application.add_handler(

        CallbackQueryHandler(

            analysis_menu,

            pattern="^analysis_menu$"

        )

    )



    # أزرار مدارس التحليل

    application.add_handler(

        CallbackQueryHandler(

            analysis_handler.handle_analysis_callback,

            pattern=
            "^(analysis_wyckoff|analysis_harmonic|analysis_classic|analysis_whales|analysis_tvl|back_main)$"

        )

    )



    # استقبال رمز العملة

    application.add_handler(

        MessageHandler(

            filters.TEXT
            &
            ~filters.COMMAND,

            analysis_handler.receive_symbol

        )

    )



    # معالجة الأخطاء

    application.add_error_handler(
        error_handler
    )



    logger.info(
        "✅ Doshka Trading Pro Started"
    )


    application.run_polling()



if __name__ == "__main__":

    main()
