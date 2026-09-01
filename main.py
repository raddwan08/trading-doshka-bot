#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from config import BOT_TOKEN, DATABASE_URL, WALLETS
from database.db_manager import DatabaseManager
from handlers.start_handler import StartHandler
from handlers.analysis_handler import AnalysisHandler
from handlers.payment_handler import PaymentHandler
from services.alert_service import AlertService
from services.crypto_api import CryptoAPI
from services.blockchain_verifier import BlockchainVerifier
from utils.keyboards import main_menu_keyboard


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


class CryptoAnalysisBot:

    def __init__(self):
        logger.info("🚀 تهيئة البوت...")

        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")

        self.db = DatabaseManager(DATABASE_URL)

        self.crypto_api = CryptoAPI()

        self.blockchain_verifier = BlockchainVerifier()

        self.application = (
            Application.builder()
            .token(BOT_TOKEN)
            .build()
        )

        self.start_handler = StartHandler(self.db)

        self.analysis_handler = AnalysisHandler(
            self.db,
            self.crypto_api
        )

        self.payment_handler = PaymentHandler(
            self.db,
            self.application,
            self.blockchain_verifier
        )

        self.alert_service = AlertService(
            self.application,
            self.db,
            self.crypto_api
        )

        self.setup_handlers()

        logger.info("✅ تم التهيئة بنجاح")


    def setup_handlers(self):

        # =========================
        # الأوامر الأساسية
        # =========================

        self.application.add_handler(
            CommandHandler(
                "start",
                self.start_handler.start
            )
        )

        self.application.add_handler(
            CommandHandler(
                "help",
                self.start_handler.help
            )
        )


        # =========================
        # الدفع
        # =========================

        self.application.add_handler(
            CommandHandler(
                "payment",
                self.payment_handler.show_payment_options
            )
        )


        # =========================
        # التحليل
        # =========================

        self.application.add_handler(
            CommandHandler(
                "analysis",
                self.analysis_handler.show_analysis_menu
            )
        )

        self.application.add_handler(
            CommandHandler(
                "price",
                self.analysis_handler.get_price
            )
        )

        self.application.add_handler(
            CommandHandler(
                "technical",
                self.analysis_handler.technical_analysis
            )
        )

        self.application.add_handler(
            CommandHandler(
                "onchain",
                self.analysis_handler.onchain_analysis
            )
        )

        self.application.add_handler(
            CommandHandler(
                "signals",
                self.analysis_handler.show_signals
            )
        )


        # =========================
        # التنبيهات
        # =========================

        self.application.add_handler(
            CommandHandler(
                "alerts",
                self.alert_service.show_alert_settings
            )
        )

        self.application.add_handler(
            CommandHandler(
                "myalerts",
                self.alert_service.show_my_alerts
            )
        )

        self.application.add_handler(
            CommandHandler(
                "deletealert",
                self.alert_service.delete_alert
            )
        )


        # =========================
        # القائمة الرئيسية
        # =========================

        self.application.add_handler(
            CallbackQueryHandler(
                self.handle_main_menu,
                pattern=(
                    "^(analysis_menu|prices_menu|"
                    "alerts_menu|payment_menu|"
                    "help_menu|back_main)$"
                )
            )
        )


        # =========================
        # الدفع
        # =========================

        self.application.add_handler(
            CallbackQueryHandler(
                self.payment_handler.handle_payment_callback,
                pattern="^payment_"
            )
        )


        # =========================
        # التحليل
        # =========================

        self.application.add_handler(
            CallbackQueryHandler(
                self.analysis_handler.handle_analysis_callback,
                pattern="^analysis_"
            )
        )


        # =========================
        # التنبيهات
        # =========================

        self.application.add_handler(
            CallbackQueryHandler(
                self.alert_service.handle_alert_callback,
                pattern="^alert_"
            )
        )


        # =========================
        # الرسائل النصية
        # =========================

        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_text_message
            )
        )


        # =========================
        # الأخطاء
        # =========================

        self.application.add_error_handler(
            self.error_handler
        )


    async def handle_main_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        query = update.callback_query

        await query.answer()

        data = query.data

        try:

            if data == "analysis_menu":

                await self.analysis_handler.show_analysis_menu(
                    update,
                    context
                )


            elif data == "prices_menu":

                await query.edit_message_text(
                    "💰 أسعار العملات\n\n"
                    "أرسل رمز العملة مثل:\n\n"
                    "BTC\n"
                    "ETH\n"
                    "SOL\n\n"
                    "أو استخدم:\n"
                    "/price BTC"
                )


            elif data == "alerts_menu":

                await self.alert_service.show_alert_settings(
                    update,
                    context
                )


            elif data == "payment_menu":

                await self.payment_handler.show_payment_options(
                    update,
                    context
                )


            elif data == "help_menu":

                await self.start_handler.help(
                    update,
                    context
                )


            elif data == "back_main":

                await query.edit_message_text(
                    "🏠 القائمة الرئيسية\n\n"
                    "اختر الخدمة:",
                    reply_markup=main_menu_keyboard()
                )


        except Exception as e:

            logger.exception(
                f"Error in main menu: {e}"
            )

            try:
                await query.message.reply_text(
                    "❌ حدث خطأ أثناء تنفيذ الطلب."
                )
            except Exception:
                pass


    async def handle_text_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        text = update.message.text.strip().upper()

        networks = {
            "SOLANA": "SOL",
            "SOL": "SOL",
            "ETHEREUM": "ETH",
            "ETH": "ETH",
            "BSC": "BSC"
        }


        if text in networks:

            network = networks[text]

            wallet = WALLETS.get(network)

            if wallet:

                await update.message.reply_text(
                    f"💳 الدفع عبر {network}\n\n"
                    f"أرسل USDT إلى:\n\n"
                    f"`{wallet}`",
                    parse_mode="Markdown"
                )

                return


        if text.isalnum() and 2 <= len(text) <= 10:

            await self.analysis_handler.get_coin_info(
                update,
                context,
                text
            )

        else:

            await update.message.reply_text(
                "🔍 أرسل رمز عملة مثل:\n"
                "BTC أو ETH أو SOL\n\n"
                "أو استخدم /help"
            )


    async def error_handler(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        logger.exception(
            f"Error: {context.error}"
        )

        try:

            if update and update.effective_message:

                await update.effective_message.reply_text(
                    "❌ حدث خطأ. حاول مرة أخرى."
                )

        except Exception:
            pass


    def run(self):

        logger.info("🚀 تشغيل البوت...")

        try:

            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES
            )

        except KeyboardInterrupt:

            logger.info("⏹️ تم إيقاف البوت")

        except Exception as e:

            logger.exception(
                f"❌ خطأ: {e}"
            )


if __name__ == "__main__":

    try:

        bot = CryptoAnalysisBot()

        bot.run()

    except Exception as e:

        logger.exception(
            f"❌ خطأ قاتل: {e}"
        )

        sys.exit(1)
