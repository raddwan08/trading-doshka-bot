import os
import logging


from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)


from handlers.analysis_handler import (
    AnalysisHandler,
    WAITING_SYMBOL
)


from services.crypto_api import CryptoAPI
from database.db import Database


from utils.keyboards import main_menu_keyboard



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


logger = logging.getLogger(__name__)



BOT_TOKEN = os.getenv(
    "BOT_TOKEN"
)


if not BOT_TOKEN:

    raise Exception(
        "BOT_TOKEN غير موجود"
    )



db = Database()


crypto_api = CryptoAPI()


analysis_handler = AnalysisHandler(
    db,
    crypto_api
)



async def start(
    update,
    context
):

    await update.message.reply_text(

        "🚀 أهلاً بك في Doshka Trading Pro\n\n"
        "اختر الخدمة:",

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



async def cancel(
    update,
    context
):

    context.user_data.clear()


    await update.message.reply_text(
        "❌ تم إلغاء العملية"
    )


    return ConversationHandler.END




def main():


    application = (

        Application
        .builder()
        .token(BOT_TOKEN)
        .build()

    )



    application.add_handler(

        CommandHandler(
            "start",
            start
        )

    )



    # قائمة التحليل

    application.add_handler(

        CallbackQueryHandler(
            analysis_menu,
            pattern="^analysis_menu$"
        )

    )



    # نظام التحليل

    analysis_conversation = ConversationHandler(

        entry_points=[

            CallbackQueryHandler(

                analysis_handler.handle_analysis_callback,

                pattern=
                "^analysis_(wyckoff|harmonic|classic|whales|tvl)$"

            )

        ],


        states={


            WAITING_SYMBOL: [

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

        ]

    )



    application.add_handler(
        analysis_conversation
    )



    application.add_handler(

        CallbackQueryHandler(

            analysis_handler.handle_analysis_callback,

            pattern="^back_main$"

        )

    )



    logger.info(
        "✅ Bot Started"
    )


    application.run_polling()



if __name__ == "__main__":

    main()
