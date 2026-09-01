import os
import logging
import asyncio


from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)


from handlers.analysis_handler import AnalysisHandler
from services.crypto_api import CryptoAPI


from utils.keyboards import (
    main_menu_keyboard
)



# =========================
# Logging
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


logger = logging.getLogger(__name__)



# =========================
# Environment
# =========================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN"
)


if not BOT_TOKEN:

    raise Exception(
        "BOT_TOKEN غير موجود"
    )



# =========================
# Database
# =========================

# اربطه مع ملف قاعدة البيانات لديك
# هنا مكان DB الحقيقي

class DummyDB:

    def check_subscription(self, user_id):

        return True



db = DummyDB()



# =========================
# Services
# =========================

crypto_api = CryptoAPI()



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
        "اختر من القائمة:",

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
# Main
# =========================


def main():


    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )



    # أمر البداية

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )



    # زر التحليل والمدارس

    application.add_handler(

        CallbackQueryHandler(

            analysis_handler.handle_analysis_callback,

            pattern=
            "^(analysis_wyckoff|analysis_harmonic|analysis_classic|analysis_whales|analysis_tvl|back_main)$"

        )

    )



    # زر قائمة التحليل

    application.add_handler(

        CallbackQueryHandler(

            analysis_menu,

            pattern="^analysis_menu$"

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



    logger.info(
        "Bot started successfully"
    )



    application.run_polling()



# =========================
# Run
# =========================

if __name__ == "__main__":

    main()
