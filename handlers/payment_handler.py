import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import ContextTypes

from config import WALLETS, SUBSCRIPTION_PLANS


logger = logging.getLogger(__name__)


class PaymentHandler:

    PAYMENT_TIMEOUT_MINUTES = 30
    PAYMENT_CHECK_INTERVAL = 20

    def __init__(
        self,
        db,
        application=None,
        blockchain_verifier=None
    ):

        self.db = db
        self.application = application
        self.blockchain_verifier = blockchain_verifier

        # حفظ مهام مراقبة الدفع
        # المفتاح: payment_id
        # القيمة: asyncio.Task
        self.payment_tasks = {}

    # ==========================================================
    # عرض خطط الدفع
    # ==========================================================

    async def show_payment_options(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        message = (
            "💳 الدفع والاشتراك\n\n"
            "اختر خطة الاشتراك:"
        )

        keyboard = []

        for plan_id, plan in SUBSCRIPTION_PLANS.items():

            button_text = (
                f"💎 {plan['name']} - "
                f"{plan['price']} USDT"
            )

            keyboard.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"payment_plan_{plan_id}"
                )
            ])

        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

    # ==========================================================
    # معالجة Callback
    # ==========================================================

    async def handle_payment_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        query = update.callback_query

        if not query:
            return

        await query.answer()

        data = query.data

        try:

            # --------------------------------------------------
            # اختيار الخطة
            # --------------------------------------------------

            if data.startswith(
                "payment_plan_"
            ):

                plan_id = data.replace(
                    "payment_plan_",
                    ""
                )

                await self._select_plan(
                    query,
                    context,
                    plan_id
                )

                return


            # --------------------------------------------------
            # اختيار الشبكة
            # --------------------------------------------------

            if data.startswith(
                "payment_network_"
            ):

                network = data.replace(
                    "payment_network_",
                    ""
                ).upper()

                await self._select_network(
                    query,
                    context,
                    network
                )

                return


            # --------------------------------------------------
            # إلغاء الدفع
            # --------------------------------------------------

            if data == "payment_cancel":

                await query.edit_message_text(
                    "❌ تم إلغاء عملية الدفع."
                )

                return


            await query.edit_message_text(
                "❌ أمر دفع غير معروف."
            )


        except Exception as e:

            logger.exception(
                f"Payment callback error: {e}"
            )

            try:

                await query.edit_message_text(
                    "❌ حدث خطأ أثناء معالجة الدفع."
                )

            except Exception:
                pass

    # ==========================================================
    # اختيار الخطة
    # ==========================================================

    async def _select_plan(
        self,
        query,
        context,
        plan_id
    ):

        plan = SUBSCRIPTION_PLANS.get(
            plan_id
        )

        if not plan:

            await query.edit_message_text(
                "❌ خطة الاشتراك غير موجودة."
            )

            return


        # حفظ الخطة مؤقتاً
        context.user_data[
            "payment_plan"
        ] = plan_id


        context.user_data[
            "payment_plan_data"
        ] = plan


        message = (
            f"💎 الخطة المختارة: "
            f"{plan['name']}\n\n"
            f"💰 السعر: "
            f"{plan['price']} USDT\n\n"
            "اختر شبكة الدفع:"
        )


        keyboard = [

            [
                InlineKeyboardButton(
                    "🔷 Solana",
                    callback_data=(
                        "payment_network_SOL"
                    )
                )
            ],

            [
                InlineKeyboardButton(
                    "🔶 Ethereum",
                    callback_data=(
                        "payment_network_ETH"
                    )
                )
            ],

            [
                InlineKeyboardButton(
                    "🟡 BSC",
                    callback_data=(
                        "payment_network_BSC"
                    )
                )
            ],

            [
                InlineKeyboardButton(
                    "❌ إلغاء",
                    callback_data=(
                        "payment_cancel"
                    )
                )
            ]
        ]


        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

    # ==========================================================
    # اختيار الشبكة وإنشاء الفاتورة
    # ==========================================================

    async def _select_network(
        self,
        query,
        context,
        network
    ):

        # ------------------------------------------------------
        # التحقق من الخطة
        # ------------------------------------------------------

        plan_id = context.user_data.get(
            "payment_plan"
        )


        plan = SUBSCRIPTION_PLANS.get(
            plan_id
        )


        if not plan:

            await query.edit_message_text(
                "❌ انتهت جلسة الدفع. "
                "ابدأ مرة أخرى باستخدام /payment"
            )

            return


        # ------------------------------------------------------
        # التحقق من الشبكة
        # ------------------------------------------------------

        if network not in WALLETS:

            await query.edit_message_text(
                "❌ شبكة غير مدعومة."
            )

            return


        wallet = WALLETS.get(
            network
        )


        if not wallet:

            await query.edit_message_text(
                "❌ عنوان المحفظة غير موجود."
            )

            return


        # ------------------------------------------------------
        # بيانات المستخدم
        # ------------------------------------------------------

        telegram_user = query.from_user

        telegram_id = (
            telegram_user.id
        )


        # ------------------------------------------------------
        # إنشاء مبلغ الدفع
        # ------------------------------------------------------

        # في الوقت الحالي نستخدم سعر الخطة مباشرة.
        #
        # لاحقاً يمكن إضافة مبلغ فريد لكل فاتورة
        # لمنع اختلاط دفعات مستخدمين مختلفين.

        amount = Decimal(
            str(plan["price"])
        )


        # ------------------------------------------------------
        # إنشاء المستخدم إذا لم يكن موجوداً
        # ------------------------------------------------------

        self.db.get_or_create_user(
            telegram_id=telegram_id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name
        )


        # ------------------------------------------------------
        # إنشاء فاتورة معلقة
        # ------------------------------------------------------

        payment = self.db.create_pending_payment(
            telegram_id=telegram_id,
            amount=float(amount),
            network=network,
            plan_type=plan_id
        )


        if not payment:

            await query.edit_message_text(
                "❌ تعذر إنشاء فاتورة الدفع."
            )

            return


        # ------------------------------------------------------
        # وقت إنشاء الفاتورة
        # ------------------------------------------------------

        invoice_created_at = datetime.now(
            timezone.utc
        )


        # ------------------------------------------------------
        # عرض معلومات الدفع
        # ------------------------------------------------------

        message = (
            "💳 فاتورة الدفع\n\n"
            f"📦 الخطة: {plan['name']}\n"
            f"💰 المبلغ: {amount} USDT\n"
            f"🌐 الشبكة: {network}\n\n"
            "📥 أرسل USDT إلى العنوان التالي:\n\n"
            f"`{wallet}`\n\n"
            "⏳ سيتم التحقق من الدفع تلقائياً.\n"
            "لا ترسل Transaction Hash.\n\n"
            f"🕒 تنتهي الفاتورة خلال "
            f"{self.PAYMENT_TIMEOUT_MINUTES} دقيقة."
        )


        keyboard = [

            [
                InlineKeyboardButton(
                    "❌ إلغاء الدفع",
                    callback_data=(
                        "payment_cancel"
                    )
                )
            ]
        ]


        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
            parse_mode="Markdown"
        )


        # ------------------------------------------------------
        # بدء مراقبة الدفع بالخلفية
        # ------------------------------------------------------

        if payment.id in self.payment_tasks:

            old_task = self.payment_tasks.get(
                payment.id
            )

            if (
                old_task
                and not old_task.done()
            ):

                old_task.cancel()


        task = asyncio.create_task(

            self._monitor_payment(

                payment_id=payment.id,

                telegram_id=telegram_id,

                network=network,

                wallet=wallet,

                amount=amount,

                plan_id=plan_id,

                duration_days=plan[
                    "duration_days"
                ],

                created_at=invoice_created_at

            )
        )


        self.payment_tasks[
            payment.id
        ] = task


        logger.info(
            f"Payment monitor started | "
            f"Payment={payment.id} | "
            f"User={telegram_id} | "
            f"Network={network}"
        )

    # ==========================================================
    # مراقبة الدفع
    # ==========================================================

    async def _monitor_payment(
        self,
        payment_id,
        telegram_id,
        network,
        wallet,
        amount,
        plan_id,
        duration_days,
        created_at
    ):

        try:

            if not self.blockchain_verifier:

                logger.error(
                    "BlockchainVerifier is not configured"
                )

                return


            # --------------------------------------------------
            # مراقبة البلوكشين
            # --------------------------------------------------

            result = (
                await self.blockchain_verifier.wait_for_payment(

                    network=network,

                    wallet=wallet,

                    expected_amount=amount,

                    created_at=created_at,

                    timeout_minutes=(
                        self.PAYMENT_TIMEOUT_MINUTES
                    ),

                    check_interval=(
                        self.PAYMENT_CHECK_INTERVAL
                    )
                )
            )


            # --------------------------------------------------
            # تم العثور على الدفع
            # --------------------------------------------------

            if result.get(
                "found"
            ):

                tx_hash = result.get(
                    "tx_hash"
                )


                if not tx_hash:

                    logger.error(
                        "Payment found but transaction "
                        "hash is missing"
                    )

                    return


                # ----------------------------------------------
                # تأكيد الدفع
                # ----------------------------------------------

                payment = (
                    self.db.complete_payment(

                        payment_id=payment_id,

                        transaction_hash=tx_hash
                    )
                )


                if not payment:

                    await self.application.bot.send_message(

                        chat_id=telegram_id,

                        text=(
                            "⚠️ تم العثور على الدفع، "
                            "لكن لم يتم تأكيده بسبب مشكلة "
                            "داخل النظام.\n\n"
                            "يرجى التواصل مع الدعم."
                        )
                    )

                    return


                # ----------------------------------------------
                # تفعيل الاشتراك
                # ----------------------------------------------

                activated = (
                    self.db.activate_subscription(

                        telegram_id=telegram_id,

                        plan_type=plan_id,

                        duration_days=duration_days
                    )
                )


                if not activated:

                    logger.error(
                        f"Failed to activate "
                        f"subscription for "
                        f"{telegram_id}"
                    )


                    await self.application.bot.send_message(

                        chat_id=telegram_id,

                        text=(
                            "⚠️ تم تأكيد الدفع، "
                            "لكن حدث خطأ أثناء تفعيل "
                            "الاشتراك.\n\n"
                            "يرجى التواصل مع الدعم."
                        )
                    )

                    return


                # ----------------------------------------------
                # إرسال النجاح
                # ----------------------------------------------

                await self.application.bot.send_message(

                    chat_id=telegram_id,

                    text=(
                        "✅ تم استلام الدفع بنجاح!\n\n"
                        "🎉 تم تفعيل اشتراكك.\n\n"
                        f"📦 الخطة: {plan_id}\n"
                        f"🌐 الشبكة: {network}\n"
                        f"💰 المبلغ: "
                        f"{result.get('amount')} USDT\n\n"
                        "شكراً لاشتراكك 💎"
                    )
                )


                logger.info(
                    f"Payment completed | "
                    f"User={telegram_id} | "
                    f"Payment={payment_id} | "
                    f"TX={tx_hash}"
                )


                return


            # --------------------------------------------------
            # انتهت الفاتورة
            # --------------------------------------------------

            status = result.get(
                "status"
            )


            if status == "expired":

                self.db.expire_payment(
                    payment_id
                )


                await self.application.bot.send_message(

                    chat_id=telegram_id,

                    text=(
                        "⌛ انتهت صلاحية فاتورة الدفع.\n\n"
                        "لم يتم العثور على الدفع خلال "
                        f"{self.PAYMENT_TIMEOUT_MINUTES} دقيقة.\n\n"
                        "يمكنك إنشاء فاتورة جديدة "
                        "باستخدام /payment"
                    )
                )


            elif status == "error":

                logger.error(
                    f"Blockchain error: {result}"
                )


                await self.application.bot.send_message(

                    chat_id=telegram_id,

                    text=(
                        "⚠️ حدث خطأ أثناء التحقق من "
                        "شبكة البلوكشين.\n\n"
                        "لم يتم تأكيد أي عملية دفع.\n"
                        "يرجى المحاولة لاحقاً."
                    )
                )


        except asyncio.CancelledError:

            logger.info(
                f"Payment monitor cancelled: "
                f"{payment_id}"
            )

            raise


        except Exception as e:

            logger.exception(
                f"Payment monitor error: {e}"
            )


            try:

                await self.application.bot.send_message(

                    chat_id=telegram_id,

                    text=(
                        "⚠️ حدث خطأ أثناء مراقبة "
                        "عملية الدفع."
                    )
                )

            except Exception:

                pass


        finally:

            # إزالة المهمة من الذاكرة

            if payment_id in self.payment_tasks:

                self.payment_tasks.pop(
                    payment_id,
                    None
                )

    # ==========================================================
    # توافق مع /verify القديم
    # ==========================================================

    async def verify_payment(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        await update.message.reply_text(
            "🤖 التحقق أصبح تلقائياً.\n\n"
            "بعد إرسال USDT إلى العنوان المطلوب، "
            "سيقوم البوت بالتحقق من الدفع "
            "وتفعيل الاشتراك تلقائياً.\n\n"
            "لا تحتاج إلى إرسال Transaction Hash."
        )

    # ==========================================================
    # الحصول على المحفظة
    # ==========================================================

    def get_wallet(
        self,
        network
    ):

        return WALLETS.get(
            network.upper()
        )
