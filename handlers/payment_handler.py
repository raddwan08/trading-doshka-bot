from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from telegram.ext import ContextTypes

from config import WALLETS

import logging

logger = logging.getLogger(__name__)


class PaymentHandler:

    def __init__(
        self,
        db,
        application=None,
        blockchain_verifier=None
    ):
        self.db = db
        self.application = application
        self.blockchain_verifier = blockchain_verifier


    # ==============================
    # عرض طرق الدفع
    # ==============================

    async def show_payment_options(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        message = (
            "💳 طرق الدفع\n\n"
            "نقبل USDT على:\n\n"
            "1️⃣ Solana\n"
            "2️⃣ Ethereum\n"
            "3️⃣ BSC\n\n"
            "اختر الشبكة:"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔷 Solana",
                    callback_data="payment_sol"
                ),

                InlineKeyboardButton(
                    "🔶 Ethereum",
                    callback_data="payment_eth"
                )
            ],

            [
                InlineKeyboardButton(
                    "🟡 BSC",
                    callback_data="payment_bsc"
                )
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # إذا تم استدعاؤها من أمر /payment
        if update.message:

            await update.message.reply_text(
                message,
                reply_markup=reply_markup
            )

        # إذا تم استدعاؤها من Callback
        elif update.callback_query:

            await update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup
            )


    # ==============================
    # اختيار شبكة الدفع
    # ==============================

    


    # ==============================
    # التحقق من الدفع
    # ==============================

    async def verify_payment(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        if not context.args:

            await update.message.reply_text(
                "❌ استخدم الأمر بهذا الشكل:\n\n"
                "/verify TRANSACTION_HASH"
            )

            return

async def handle_payment_callback(
    self,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    try:
        if query is None:
            logger.error("Callback query is None")
            return

        await query.answer()

        data = query.data

        logger.info(f"Payment callback data: {data}")

        network_map = {
            "payment_sol": "SOL",
            "payment_eth": "ETH",
            "payment_bsc": "BSC"
        }

        network = network_map.get(data)

        if not network:

            logger.error(f"Unknown payment callback: {data}")

            await query.edit_message_text(
                "❌ شبكة غير معروفة."
            )

            return


        wallet = WALLETS.get(network)

        logger.info(
            f"Network selected: {network}"
        )

        logger.info(
            f"Wallet exists: {wallet is not None}"
        )


        if not wallet:

            await query.edit_message_text(
                f"❌ محفظة {network} غير مهيأة في السيرفر."
            )

            return


        # حفظ الشبكة للمستخدم
        context.user_data["payment_network"] = network


        network_names = {
            "SOL": "Solana",
            "ETH": "Ethereum",
            "BSC": "BSC"
        }


        network_name = network_names.get(
            network,
            network
        )


        message = (
            f"💳 الدفع عبر {network_name}\n\n"
            f"💰 العملة: USDT\n"
            f"🌐 الشبكة: {network_name}\n\n"
            f"📬 عنوان المحفظة:\n\n"
            f"<code>{wallet}</code>\n\n"
            f"⚠️ أرسل USDT على نفس الشبكة فقط.\n\n"
            f"بعد التحويل أرسل:\n"
            f"/verify TRANSACTION_HASH"
        )


        await query.edit_message_text(
            message,
            parse_mode="HTML"
        )


        logger.info(
            f"Payment network {network} displayed successfully"
        )


    except Exception as e:

        logger.exception(
            f"Payment callback error: {e}"
        )

        try:
            await query.answer(
                "حدث خطأ أثناء معالجة الدفع",
                show_alert=True
            )
        except Exception:
            pass
        tx_hash = context.args[0]


        await update.message.reply_text(
            "⏳ جاري التحقق من المعاملة..."
        )


        try:

            # تأكد من وجود خدمة التحقق
            if not self.blockchain_verifier:

                await update.message.reply_text(
                    "❌ خدمة التحقق من المدفوعات غير متاحة حالياً."
                )

                return


            # سيتم ربط التحقق الحقيقي هنا
            logger.info(
                f"Verifying transaction: {tx_hash}"
            )


        except Exception as e:

            logger.exception(
                f"Verification error: {e}"
            )

            await update.message.reply_text(
                "❌ حدث خطأ أثناء التحقق من المعاملة."
            )


    # ==============================
    # الحصول على المحفظة
    # ==============================

    def get_wallet(self, network):

        return WALLETS.get(
            network.upper()
        )
