import logging

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from telegram.ext import ContextTypes

from config import SUBSCRIPTION_PLANS


logger = logging.getLogger(__name__)


class SubscriptionHandler:

    def __init__(self, db):
        self.db = db


    # ==========================================================
    # عرض خطط الاشتراك
    # ==========================================================

    async def show_plans(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        message = (
            "💎 خطط الاشتراك\n\n"
            "📅 شهري — 25 USDT\n"
            "📅 3 أشهر — 60 USDT\n"
            "📅 6 أشهر — 100 USDT\n"
            "👑 سنوي — 180 USDT\n\n"
            "👇 اختر خطة الاشتراك:"
        )

        keyboard = [

            [
                InlineKeyboardButton(
                    "📅 شهري — 25 USDT",
                    callback_data="subscribe_monthly"
                )
            ],

            [
                InlineKeyboardButton(
                    "📅 3 أشهر — 60 USDT",
                    callback_data="subscribe_quarterly"
                )
            ],

            [
                InlineKeyboardButton(
                    "📅 6 أشهر — 100 USDT",
                    callback_data="subscribe_half_yearly"
                )
            ],

            [
                InlineKeyboardButton(
                    "👑 سنوي — 180 USDT",
                    callback_data="subscribe_yearly"
                )
            ]

        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        try:

            # عند استخدام /subscribe
            if update.message:

                await update.message.reply_text(
                    message,
                    reply_markup=reply_markup
                )

                return


            # عند فتح الاشتراك من زر القائمة
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
                f"Error showing subscription plans: {e}"
            )

            raise


    # ==========================================================
    # معالجة اختيار الخطة
    # ==========================================================

    async def handle_subscription_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        query = update.callback_query

        if query is None:

            logger.error(
                "Subscription callback without callback query"
            )

            return


        try:

            await query.answer()

            data = query.data

            logger.info(
                f"Subscription callback: {data}"
            )


            # ==============================================
            # اختيار الخطة
            # ==============================================

            plan_map = {

                "subscribe_monthly": "monthly",

                "subscribe_quarterly": "quarterly",

                "subscribe_half_yearly": "half_yearly",

                "subscribe_yearly": "yearly"

            }


            plan_key = plan_map.get(data)


            if plan_key:

                plan = SUBSCRIPTION_PLANS.get(plan_key)


                if not plan:

                    await query.edit_message_text(
                        "❌ الخطة غير موجودة."
                    )

                    return


                # حفظ الخطة للمستخدم
                context.user_data[
                    "subscription_plan"
                ] = plan_key


                context.user_data[
                    "subscription_price"
                ] = plan["price"]


                context.user_data[
                    "subscription_duration"
                ] = plan["duration_days"]


                message = (
                    "💎 تم اختيار خطة الاشتراك\n\n"
                    f"📅 الخطة: {plan['name']}\n"
                    f"💰 السعر: {plan['price']} USDT\n"
                    f"⏳ المدة: {plan['duration_days']} يوم\n\n"
                    "👇 اختر شبكة الدفع:"
                )


                keyboard = [

                    [
                        InlineKeyboardButton(
                            "🔷 Solana",
                            callback_data="subscribe_network_sol"
                        ),

                        InlineKeyboardButton(
                            "🔶 Ethereum",
                            callback_data="subscribe_network_eth"
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            "🟡 BSC",
                            callback_data="subscribe_network_bsc"
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            "🔙 تغيير الخطة",
                            callback_data="subscribe_back_plans"
                        )
                    ]

                ]


                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(
                        keyboard
                    )
                )

                return


            # ==============================================
            # العودة إلى الخطط
            # ==============================================

            if data == "subscribe_back_plans":

                await self.show_plans(
                    update,
                    context
                )

                return


            # ==============================================
            # اختيار شبكة الدفع
            # ==============================================

            network_map = {

                "subscribe_network_sol": "SOL",

                "subscribe_network_eth": "ETH",

                "subscribe_network_bsc": "BSC"

            }


            network = network_map.get(data)


            if network:

                # التأكد من اختيار خطة أولاً
                plan_key = context.user_data.get(
                    "subscription_plan"
                )


                if not plan_key:

                    await query.edit_message_text(
                        "❌ يجب اختيار خطة الاشتراك أولاً."
                    )

                    return


                # حفظ شبكة الدفع
                context.user_data[
                    "payment_network"
                ] = network


                context.user_data[
                    "subscription_payment_network"
                ] = network


                # تحويل المستخدم إلى PaymentHandler
                #
                # نرسل Callback جديد يمكن لـ PaymentHandler التعامل معه

                from config import WALLETS

                wallet = WALLETS.get(network)


                if not wallet:

                    await query.edit_message_text(
                        f"❌ محفظة {network} غير مهيأة."
                    )

                    return


                plan = SUBSCRIPTION_PLANS.get(
                    plan_key
                )


                network_names = {

                    "SOL": "Solana",

                    "ETH": "Ethereum (ERC-20)",

                    "BSC": "BNB Smart Chain (BEP-20)"

                }


                network_name = network_names.get(
                    network,
                    network
                )


                message = (
                    "💳 معلومات الدفع\n\n"
                    f"💎 الخطة: {plan['name']}\n"
                    f"💰 المبلغ المطلوب: "
                    f"{plan['price']} USDT\n"
                    f"📅 المدة: "
                    f"{plan['duration_days']} يوم\n\n"
                    f"🌐 الشبكة: {network_name}\n\n"
                    "📬 أرسل المبلغ إلى:\n\n"
                    f"<code>{wallet}</code>\n\n"
                    "⚠️ أرسل USDT على نفس الشبكة فقط.\n\n"
                    "بعد التحويل أرسل:\n"
                    "<code>/verify TRANSACTION_HASH</code>"
                )


                keyboard = [

                    [
                        InlineKeyboardButton(
                            "🔙 تغيير الشبكة",
                            callback_data=(
                                "subscribe_back_network"
                            )
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            "💎 تغيير الخطة",
                            callback_data=(
                                "subscribe_back_plans"
                            )
                        )
                    ]

                ]


                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(
                        keyboard
                    ),
                    parse_mode="HTML"
                )


                logger.info(
                    f"Subscription payment selected | "
                    f"Plan: {plan_key} | "
                    f"Network: {network}"
                )

                return


            # ==============================================
            # الرجوع إلى اختيار الشبكة
            # ==============================================

            if data == "subscribe_back_network":

                plan_key = context.user_data.get(
                    "subscription_plan"
                )


                if not plan_key:

                    await self.show_plans(
                        update,
                        context
                    )

                    return


                plan = SUBSCRIPTION_PLANS.get(
                    plan_key
                )


                message = (
                    "💳 اختر شبكة الدفع\n\n"
                    f"💎 الخطة: {plan['name']}\n"
                    f"💰 السعر: {plan['price']} USDT\n\n"
                    "👇 اختر الشبكة:"
                )


                keyboard = [

                    [

                        InlineKeyboardButton(
                            "🔷 Solana",
                            callback_data=(
                                "subscribe_network_sol"
                            )
                        ),

                        InlineKeyboardButton(
                            "🔶 Ethereum",
                            callback_data=(
                                "subscribe_network_eth"
                            )
                        )

                    ],

                    [

                        InlineKeyboardButton(
                            "🟡 BSC",
                            callback_data=(
                                "subscribe_network_bsc"
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

                return


            # ==============================================
            # البيانات القديمة
            # ==============================================

            if data == "subscribe_now":

                await self.show_plans(
                    update,
                    context
                )

                return


            logger.warning(
                f"Unknown subscription callback: {data}"
            )


        except Exception as e:

            logger.exception(
                f"Subscription callback error: {e}"
            )


            try:

                await query.answer(
                    "حدث خطأ أثناء معالجة الاشتراك",
                    show_alert=True
                )

            except Exception:

                pass
