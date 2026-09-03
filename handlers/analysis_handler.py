# handlers/analysis_handler.py

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from utils.keyboards import (
    analysis_keyboard,
    main_menu_keyboard
)

from services.chart_service import ChartService

from analysis import (
    wyckoff,
    harmonic,
    classic,
    whales,
    tvl
)


logger = logging.getLogger(__name__)

WAITING_SYMBOL = 1


class AnalysisHandler:

    def __init__(self, db, crypto_api):
        self.db = db
        self.crypto_api = crypto_api


    async def show_analysis_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        await update.effective_message.reply_text(
            "📊 مدارس التحليل\n\n"
            "اختر مدرسة التحليل:",
            reply_markup=analysis_keyboard()
        )


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
                "🔒 تحليل TVL"

        }


        if data in schools:

            context.user_data["analysis_school"] = data


            await query.edit_message_text(

                f"{schools[data]}\n\n"
                "🪙 أرسل رمز العملة للتحليل\n\n"
                "مثال:\n"
                "BTC"

            )

            return WAITING_SYMBOL



        if data == "back_main":

            context.user_data.clear()

            await query.edit_message_text(
                "🏠 القائمة الرئيسية",
                reply_markup=main_menu_keyboard()
            )

            return ConversationHandler.END



        return ConversationHandler.END



    async def receive_symbol(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        if update.message is None:
            return WAITING_SYMBOL


        symbol = update.message.text.strip().upper()

        symbol = (
            symbol
            .replace("USDT", "")
            .replace("/", "")
            .replace(" ", "")
        )


        school = context.user_data.get(
            "analysis_school"
        )


        if not school:

            await update.message.reply_text(
                "❌ لم يتم اختيار مدرسة التحليل"
            )

            return ConversationHandler.END



        await update.message.reply_text(
            f"⏳ جاري تحليل {symbol}..."
        )


        try:

            result = None


            if school == "analysis_tvl":

                data = await self.crypto_api.get_tvl(
                    symbol
                )

                if data:

                    result = tvl.analyze(data)



            else:

                candles = await self.crypto_api.get_klines(
                    symbol,
                    interval="4h",
                    limit=100
                )


                if not candles:

                    await update.message.reply_text(
                        "❌ لا توجد بيانات لهذه العملة"
                    )

                    return ConversationHandler.END



                if school == "analysis_wyckoff":

                    result = wyckoff.analyze(
                        candles
                    )


                elif school == "analysis_harmonic":

                    result = harmonic.analyze(
                        candles
                    )


                elif school == "analysis_classic":

                    result = classic.analyze(
                        candles
                    )


                elif school == "analysis_whales":

                    result = whales.analyze(
                        candles
                    )



            if not result:

                await update.message.reply_text(
                    "❌ فشل إنشاء التحليل"
                )

                return ConversationHandler.END



            message = (

                "📊 Doshka Trading Pro\n\n"
                f"🪙 العملة: {symbol}\n\n"
                f"🏫 المدرسة: "
                f"{result.get('school','')}\n\n"
                f"🎯 الإشارة: "
                f"{result.get('signal','WAIT')}\n\n"
                f"{result.get('message','')}"

            )


            if "rsi" in result:

                message += (
                    f"\n\n📊 RSI: {result['rsi']}"
                )


            if "support" in result:

                message += (
                    f"\n📉 الدعم: {result['support']}"
                    f"\n📈 المقاومة: {result.get('resistance','')}"
                )


            if "volume_ratio" in result:

                message += (
                    f"\n🐋 قوة الحجم: "
                    f"{result['volume_ratio']}x"
                )


            if result.get("pattern"):

                message += (
                    f"\n🦋 النموذج: "
                    f"{result['pattern']}"
                )


            await update.message.reply_text(
                message
            )


            context.user_data.pop(
                "analysis_school",
                None
            )


            return ConversationHandler.END



        except Exception as e:

            logger.exception(
                f"Analysis error: {e}"
            )


            await update.message.reply_text(
                "❌ حدث خطأ أثناء التحليل"
            )


            return ConversationHandler.END
