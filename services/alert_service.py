from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)


class AlertService:

    def __init__(self, application, db, crypto_api):
        self.application = application
        self.db = db
        self.crypto_api = crypto_api


    async def show_alert_settings(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        message = (
            "🔔 التنبيهات\n\n"
            "اختر نوع التنبيه:"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "💰 تنبيه السعر",
                    callback_data="alert_price"
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 تنبيه التغير",
                    callback_data="alert_change"
                )
            ],
            [
                InlineKeyboardButton(
                    "📋 تنبيهاتي",
                    callback_data="alert_myalerts"
                )
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        try:

            # إذا تم فتح التنبيهات من زر القائمة
            if update.callback_query:

                query = update.callback_query

                await query.answer()

                await query.edit_message_text(
                    message,
                    reply_markup=reply_markup
                )

            # إذا تم فتحها بواسطة /alerts
            elif update.message:

                await update.message.reply_text(
                    message,
                    reply_markup=reply_markup
                )

        except Exception as e:

            logger.exception(
                f"Error showing alert settings: {e}"
            )

            try:
                if update.effective_message:
                    await update.effective_message.reply_text(
                        "❌ حدث خطأ أثناء فتح التنبيهات."
                    )
            except Exception:
                pass


    async def handle_alert_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        query = update.callback_query

        if not query:
            return

        await query.answer()

        try:

            # =========================
            # تنبيه السعر
            # =========================

            if query.data == "alert_price":

                context.user_data["alert_mode"] = "price"

                await query.edit_message_text(
                    "💰 تنبيه السعر\n\n"
                    "أرسل رمز العملة والسعر.\n\n"
                    "مثال:\n"
                    "`BTC 50000`",
                    parse_mode="Markdown"
                )


            # =========================
            # تنبيه نسبة التغير
            # =========================

            elif query.data == "alert_change":

                context.user_data["alert_mode"] = "change"

                await query.edit_message_text(
                    "📊 تنبيه التغير\n\n"
                    "أرسل رمز العملة ونسبة التغير.\n\n"
                    "مثال:\n"
                    "`BTC 5`",
                    parse_mode="Markdown"
                )


            # =========================
            # عرض التنبيهات
            # =========================

            elif query.data == "alert_myalerts":

                user_id = update.effective_user.id

                alerts = self.db.get_user_alerts(user_id)

                if not alerts:

                    await query.edit_message_text(
                        "📭 لا توجد لديك تنبيهات حالياً."
                    )

                    return

                message = "🔔 تنبيهاتك الحالية:\n\n"

                keyboard = []

                for alert in alerts:

                    message += (
                        f"• {alert.symbol}\n"
                        f"النوع: {alert.condition_type}\n"
                        f"السعر/النسبة: {alert.threshold}\n\n"
                    )

                    keyboard.append([
                        InlineKeyboardButton(
                            f"❌ حذف {alert.symbol}",
                            callback_data=f"alert_delete_{alert.id}"
                        )
                    ])

                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )


            # =========================
            # حذف تنبيه
            # =========================

            elif query.data.startswith("alert_delete_"):

                alert_id = int(
                    query.data.replace(
                        "alert_delete_",
                        ""
                    )
                )

                user_id = update.effective_user.id

                success = self.db.delete_alert(
                    alert_id,
                    user_id
                )

                if success:

                    await query.answer(
                        "تم حذف التنبيه بنجاح"
                    )

                    await query.edit_message_text(
                        "✅ تم حذف التنبيه بنجاح."
                    )

                else:

                    await query.edit_message_text(
                        "❌ لم يتم العثور على التنبيه."
                    )


        except Exception as e:

            logger.exception(
                f"Error handling alert callback: {e}"
            )

            try:

                await query.edit_message_text(
                    "❌ حدث خطأ أثناء تنفيذ العملية."
                )

            except Exception:
                pass


    async def show_my_alerts(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        user_id = update.effective_user.id

        try:

            alerts = self.db.get_user_alerts(user_id)

            if not alerts:

                await update.effective_message.reply_text(
                    "📭 لا توجد لديك تنبيهات حالياً."
                )

                return

            message = "🔔 تنبيهاتك الحالية:\n\n"

            keyboard = []

            for alert in alerts:

                message += (
                    f"• {alert.symbol}\n"
                    f"النوع: {alert.condition_type}\n"
                    f"القيمة: {alert.threshold}\n\n"
                )

                keyboard.append([
                    InlineKeyboardButton(
                        f"❌ حذف {alert.symbol}",
                        callback_data=f"alert_delete_{alert.id}"
                    )
                ])

            await update.effective_message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:

            logger.exception(
                f"Error showing user alerts: {e}"
            )

            await update.effective_message.reply_text(
                "❌ حدث خطأ أثناء جلب التنبيهات."
            )


    async def delete_alert(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        if not context.args:

            await update.effective_message.reply_text(
                "❌ استخدم الأمر بهذا الشكل:\n\n"
                "/deletealert رقم_التنبيه"
            )

            return

        try:

            alert_id = int(context.args[0])

            user_id = update.effective_user.id

            success = self.db.delete_alert(
                alert_id,
                user_id
            )

            if success:

                await update.effective_message.reply_text(
                    "✅ تم حذف التنبيه بنجاح."
                )

            else:

                await update.effective_message.reply_text(
                    "❌ لم يتم العثور على التنبيه."
                )

        except ValueError:

            await update.effective_message.reply_text(
                "❌ رقم التنبيه غير صحيح."
            )

        except Exception as e:

            logger.exception(
                f"Error deleting alert: {e}"
            )

            await update.effective_message.reply_text(
                "❌ حدث خطأ أثناء حذف التنبيه."
            )


    async def create_alert_from_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str
    ):

        mode = context.user_data.get("alert_mode")

        if not mode:
            return False

        try:

            parts = text.strip().upper().split()

            if len(parts) != 2:

                await update.message.reply_text(
                    "❌ الصيغة غير صحيحة.\n\n"
                    "مثال:\n"
                    "BTC 50000"
                )

                return True

            symbol = parts[0]

            value = parts[1].replace("%", "")

            threshold = float(value)

            user_id = update.effective_user.id

            if mode == "price":

                condition_type = "price"

            elif mode == "change":

                condition_type = "change"

            else:

                return False

            alert = self.db.create_alert(
                telegram_id=user_id,
                symbol=symbol,
                condition_type=condition_type,
                threshold=threshold
            )

            if alert:

                await update.message.reply_text(
                    "✅ تم إنشاء التنبيه بنجاح!\n\n"
                    f"العملة: {symbol}\n"
                    f"النوع: {condition_type}\n"
                    f"القيمة: {threshold}"
                )

                context.user_data.pop(
                    "alert_mode",
                    None
                )

            else:

                await update.message.reply_text(
                    "❌ حدث خطأ أثناء إنشاء التنبيه."
                )

            return True

        except ValueError:

            await update.message.reply_text(
                "❌ القيمة المدخلة غير صحيحة."
            )

            return True

        except Exception as e:

            logger.exception(
                f"Error creating alert: {e}"
            )

            await update.message.reply_text(
                "❌ حدث خطأ أثناء إنشاء التنبيه."
            )

            return True
