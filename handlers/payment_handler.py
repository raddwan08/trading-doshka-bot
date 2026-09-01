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
    """
    مسؤول عن:
    - عرض شبكات الدفع
    - اختيار الشبكة
    - عرض عنوان المحفظة
    - حفظ الشبكة المختارة للمستخدم
    - استقبال Transaction Hash للتحقق
    """

    def __init__(
        self,
        db,
        application=None,
        blockchain_verifier=None
    ):
        self.db = db
        self.application = application
        self.blockchain_verifier = blockchain_verifier


    # ==========================================================
    # عرض خيارات الدفع
    # ==========================================================

    async def show_payment_options(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        message = (
            "💳 طرق الدفع\n\n"
            "نقبل USDT على الشبكات التالية:\n\n"
            "1️⃣ Solana\n"
            "2️⃣ Ethereum\n"
            "3️⃣ BSC\n\n"
            "👇 اختر الشبكة:"
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
            ],

            [
                InlineKeyboardButton(
                    "🏠 القائمة الرئيسية",
                    callback_data="back_main"
                )
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        try:

            # إذا تم فتح الدفع من أمر /payment
            if update.message:

                await update.message.reply_text(
                    message,
                    reply_markup=reply_markup
                )

                return


            # إذا تم فتح الدفع من زر Callback
            if update.callback_query:

                query = update.callback_query

                await query.answer()

                await query.edit_message_text(
                    message,
                    reply_markup=reply_markup
                )

                return


        except Exception as e:

            logger.exception(
                f"Error showing payment options: {e}"
            )

            raise


    # ==========================================================
    # معالجة اختيار شبكة الدفع
    # ==========================================================

    async def handle_payment_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        query = update.callback_query

        if query is None:

            logger.error(
                "Payment callback called without callback_query"
            )

            return


        try:

            # إيقاف علامة التحميل في Telegram
            await query.answer()

            data = query.data

            logger.info(
                f"Payment callback received: {data}"
            )


            # ربط بيانات الأزرار بالشبكات
            network_map = {

                "payment_sol": "SOL",

                "payment_eth": "ETH",

                "payment_bsc": "BSC"

            }


            network = network_map.get(data)


            # التحقق من الشبكة
            if network is None:

                logger.warning(
                    f"Unknown payment callback: {data}"
                )

                await query.edit_message_text(
                    "❌ شبكة دفع غير معروفة."
                )

                return


            # الحصول على المحفظة
            wallet = WALLETS.get(network)


            logger.info(
                f"Selected network: {network}"
            )

            logger.info(
                f"Wallet configured: {bool(wallet)}"
            )


            # التحقق من وجود المحفظة
            if not wallet:

                await query.edit_message_text(
                    f"❌ محفظة شبكة {network} غير مهيأة في السيرفر."
                )

                return


            # ==================================================
            # حفظ الشبكة المختارة للمستخدم
            # ==================================================

            context.user_data["payment_network"] = network


            # ==================================================
            # أسماء الشبكات للعرض
            # ==================================================

            network_names = {

                "SOL": "Solana",

                "ETH": "Ethereum (ERC-20)",

                "BSC": "BNB Smart Chain (BEP-20)"

            }


            network_name = network_names.get(
                network,
                network
            )


            # ==================================================
            # رسالة الدفع
            # ==================================================

            message = (
                f"💳 الدفع عبر {network_name}\n\n"
                f"💰 العملة: USDT\n"
                f"🌐 الشبكة: {network_name}\n\n"
                f"📬 عنوان المحفظة:\n\n"
                f"<code>{wallet}</code>\n\n"
                f"⚠️ مهم جداً:\n"
                f"أرسل USDT على نفس الشبكة فقط.\n\n"
                f"بعد التحويل أرسل:\n"
                f"/verify TRANSACTION_HASH"
            )


            # زر الرجوع إلى شبكات الدفع
            keyboard = [

                [
                    InlineKeyboardButton(
                        "🔙 تغيير الشبكة",
                        callback_data="payment_back"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "💳 طرق الدفع",
                        callback_data="payment_options"
                    )
                ]

            ]


            reply_markup = InlineKeyboardMarkup(
                keyboard
            )


            await query.edit_message_text(
                message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )


            logger.info(
                f"Payment information sent successfully: {network}"
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

            except Exception as callback_error:

                logger.error(
                    f"Could not send callback error: "
                    f"{callback_error}"
                )


    # ==========================================================
    # زر تغيير الشبكة / العودة لخيارات الدفع
    # ==========================================================

    async def handle_payment_navigation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        query = update.callback_query

        if query is None:
            return


        try:

            await query.answer()

            await self.show_payment_options(
                update,
                context
            )


        except Exception as e:

            logger.exception(
                f"Payment navigation error: {e}"
            )


    # ==========================================================
    # التحقق من الدفع
    # ==========================================================

    async def verify_payment(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        try:

            # التحقق من وجود Transaction Hash
            if not context.args:

                await update.message.reply_text(
                    "❌ لم ترسل Transaction Hash.\n\n"
                    "استخدم الأمر بهذا الشكل:\n\n"
                    "<code>/verify TRANSACTION_HASH</code>",
                    parse_mode="HTML"
                )

                return


            # أخذ الهاش
            tx_hash = context.args[0].strip()


            # الشبكة التي اختارها المستخدم
            network = context.user_data.get(
                "payment_network"
            )


            # إذا لم يختر المستخدم شبكة
            if not network:

                await update.message.reply_text(
                    "❌ يجب اختيار شبكة الدفع أولاً.\n\n"
                    "استخدم:\n"
                    "/payment"
                )

                return


            # التحقق من وجود المحفظة
            wallet = WALLETS.get(network)


            if not wallet:

                await update.message.reply_text(
                    f"❌ محفظة {network} غير مهيأة."
                )

                return


            # رسالة انتظار
            await update.message.reply_text(
                "⏳ جاري التحقق من المعاملة...\n\n"
                f"🌐 الشبكة: {network}\n"
                f"🔗 المعاملة:\n"
                f"<code>{tx_hash}</code>",
                parse_mode="HTML"
            )


            logger.info(
                f"Payment verification requested | "
                f"Network: {network} | "
                f"User: {update.effective_user.id}"
            )


            # ==================================================
            # التحقق الفعلي
            # ==================================================

            if self.blockchain_verifier is None:

                logger.warning(
                    "BlockchainVerifier is not configured"
                )

                await update.message.reply_text(
                    "⚠️ تم استلام المعاملة، "
                    "لكن خدمة التحقق غير مهيأة حالياً."
                )

                return


            # في الوقت الحالي لا نفترض اسم الدالة
            # لأننا لم نر ملف blockchain_verifier.py بعد.
            #
            # سيتم ربط التحقق الحقيقي هنا بعد مراجعة الملف.


            await update.message.reply_text(
                "✅ تم استلام Transaction Hash.\n\n"
                "سيتم التحقق من المعاملة على الشبكة المختارة."
            )


        except Exception as e:

            logger.exception(
                f"Payment verification error: {e}"
            )


            await update.message.reply_text(
                "❌ حدث خطأ أثناء التحقق من المعاملة."
            )


    # ==========================================================
    # الحصول على عنوان المحفظة
    # ==========================================================

    def get_wallet(
        self,
        network: str
    ):

        if not network:

            return None


        return WALLETS.get(
            network.upper()
        )
