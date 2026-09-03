import os
import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from utils.keyboards import (
    analysis_keyboard,
    main_menu_keyboard
)

from analysis import (
    wyckoff,
    harmonic,
    classic,
    whales,
    tvl
)

from services.chart_service import ChartService


logger = logging.getLogger(__name__)


WAITING_SYMBOL = 1


class AnalysisHandler:


    def __init__(
        self,
        db,
        crypto_api
    ):

        self.db = db

        self.crypto_api = crypto_api

        self.chart_service = ChartService()


    # =========================
    # SHOW ANALYSIS MENU
    # =========================

    async def show_analysis_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        message = update.effective_message


        await message.reply_text(

            "📊 مدارس التحليل\n\n"
            "اختر مدرسة التحليل:",

            reply_markup=analysis_keyboard()

        )


    # =========================
    # ANALYSIS CALLBACK
    # =========================

    async def handle_analysis_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        query = update.callback_query


        if query is None:

            return ConversationHandler.END


        await query.answer()


        data = query.data


        schools = {

            "analysis_wyckoff":
                "📈 تحليل وايكوف",

            "analysis_harmonic":
                "🦋 تحليل هارمونيك",

            "analysis_classic":
                "📉 التحليل الكلاسيكي",

            "analysis_whales":
                "🐋 تحليل الحيتان",

            "analysis_tvl":
                "🔒 تحليل TVL",

        }


        # اختيار مدرسة التحليل

        if data in schools:

            context.user_data[
                "analysis_school"
            ] = data


            await query.edit_message_text(

                f"{schools[data]}\n\n"
                "🪙 أرسل رمز العملة للتحليل\n\n"
                "مثال:\n"
                "BTC"

            )


            return WAITING_SYMBOL


        # إلغاء التحليل

        if data == "analysis_cancel":

            context.user_data.clear()


            await query.edit_message_text(

                "❌ تم إلغاء التحليل.",

                reply_markup=main_menu_keyboard()

            )


            return ConversationHandler.END


        # العودة للقائمة الرئيسية

        if data == "back_main":

            context.user_data.clear()


            await query.edit_message_text(

                "🏠 القائمة الرئيسية",

                reply_markup=main_menu_keyboard()

            )


            return ConversationHandler.END


        return ConversationHandler.END


    # =========================
    # RECEIVE SYMBOL
    # =========================

    async def receive_symbol(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):


        if update.message is None:

            return WAITING_SYMBOL


        if not update.message.text:

            return WAITING_SYMBOL


        # الحصول على مدرسة التحليل

        school = context.user_data.get(
            "analysis_school"
        )


        if school is None:

            await update.message.reply_text(

                "❌ لم يتم اختيار مدرسة التحليل.",

                reply_markup=main_menu_keyboard()

            )


            return ConversationHandler.END


        # تنظيف رمز العملة

        symbol = (
            update.message.text
            .strip()
            .upper()
        )


        symbol = (
            symbol
            .replace("USDT", "")
            .replace("/", "")
            .replace(" ", "")
        )


        if not symbol:

            await update.message.reply_text(

                "❌ أرسل رمز عملة صحيحاً."

            )


            return WAITING_SYMBOL


        # رسالة التحميل

        await update.message.reply_text(

            f"⏳ جاري تحليل {symbol}..."

        )


        try:


            result = None

            candles = None


            # =========================
            # TVL ANALYSIS
            # =========================

            if school == "analysis_tvl":


                tvl_data = (
                    await self.crypto_api.get_tvl(
                        symbol
                    )
                )


                if not tvl_data:

                    await update.message.reply_text(

                        "❌ لا توجد بيانات TVL لهذه العملة."

                    )


                    return ConversationHandler.END


                result = tvl.analyze(
                    tvl_data
                )


            # =========================
            # PRICE ANALYSIS
            # =========================

            else:


                candles = (
                    await self.crypto_api.get_klines(

                        symbol,

                        interval="4h",

                        limit=100

                    )
                )


                if not candles:

                    await update.message.reply_text(

                        f"❌ لا توجد بيانات للعملة {symbol}."

                    )


                    return ConversationHandler.END


                # =====================
                # WYCKOFF
                # =====================

                if school == "analysis_wyckoff":

                    result = wyckoff.analyze(
                        candles
                    )


                # =====================
                # HARMONIC
                # =====================

                elif school == "analysis_harmonic":

                    result = harmonic.analyze(
                        candles
                    )


                # =====================
                # CLASSIC
                # =====================

                elif school == "analysis_classic":

                    result = classic.analyze(
                        candles
                    )


                # =====================
                # WHALES
                # =====================

                elif school == "analysis_whales":

                    result = whales.analyze(
                        candles
                    )


            # =========================
            # CHECK RESULT
            # =========================

            if not result:

                await update.message.reply_text(

                    "❌ فشل إنشاء التحليل."

                )


                return ConversationHandler.END


            # =========================
            # CREATE CHART
            # =========================

            chart_path = None


            if (
                school != "analysis_tvl"
                and candles
            ):


                try:


                    chart_path = (
    self.chart_service.create_chart(

        symbol=symbol,

        candles=candles,

        school=school,

        result=result

    )
)


                except Exception as e:


                    logger.exception(

                        f"Chart error: {e}"

                    )


            # =========================
            # CREATE MESSAGE
            # =========================

            message = (

                "📊 Doshka Trading Pro\n\n"

                f"🪙 العملة: {symbol}\n"

                f"🏫 المدرسة: "
                f"{result.get('school', '')}\n\n"

                f"🎯 الإشارة: "
                f"{result.get('signal', 'WAIT')}\n\n"

                f"{result.get('message', '')}"

            )


            # RSI

            if result.get("rsi") is not None:

                message += (

                    f"\n\n📊 RSI: "
                    f"{result.get('rsi')}"

                )


            # SUPPORT

            if result.get("support") is not None:

                message += (

                    f"\n📉 الدعم: "
                    f"{result.get('support')}"

                )


            # RESISTANCE

            if result.get("resistance") is not None:

                message += (

                    f"\n📈 المقاومة: "
                    f"{result.get('resistance')}"

                )


            # VOLUME

            if result.get(
                "volume_ratio"
            ) is not None:

                message += (

                    f"\n🐋 قوة الحجم: "

                    f"{result.get('volume_ratio')}x"

                )


            # PATTERN

            if result.get("pattern"):

                message += (

                    f"\n🦋 النموذج: "

                    f"{result.get('pattern')}"

                )


            # =========================
            # SEND CHART
            # =========================

            if (

                chart_path

                and

                os.path.exists(
                    chart_path
                )

            ):


                with open(

                    chart_path,

                    "rb"

                ) as chart:


                    await update.message.reply_photo(

                        photo=chart,

                        caption=message

                    )


                # حذف الملف بعد الإرسال

                try:

                    os.remove(
                        chart_path
                    )

                except Exception:

                    pass


            else:


                await update.message.reply_text(

                    message

                )


            # =========================
            # CLEAR USER DATA
            # =========================

            context.user_data.pop(

                "analysis_school",

                None

            )


            return ConversationHandler.END


        except Exception as error:


            logger.exception(

                "Analysis error: %s",

                error

            )


            await update.message.reply_text(

                "❌ حدث خطأ أثناء تنفيذ التحليل."

            )


            context.user_data.pop(

                "analysis_school",

                None

            )


            return ConversationHandler.END
