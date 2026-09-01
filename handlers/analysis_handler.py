# handlers/analysis_handler.py

from telegram import Update
from telegram.ext import ContextTypes
from utils.keyboards import analysis_keyboard
from utils.keyboards import main_menu_keyboard

from analysis import (
    wyckoff,
    harmonic,
    classic,
    whales,
    tvl
)

import logging


logger = logging.getLogger(__name__)


class AnalysisHandler:


    def __init__(
        self,
        db,
        crypto_api
    ):

        self.db = db
        self.crypto_api = crypto_api



    async def show_analysis_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        await update.message.reply_text(

            "📊 مدارس التحليل\n\n"
            "اختر نوع التحليل:",

            reply_markup=analysis_keyboard()

        )



    async def handle_analysis_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):


        query = update.callback_query

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


            context.user_data[
                "analysis_school"
            ] = data



            await query.edit_message_text(

                f"{schools[data]}\n\n"
                "أرسل رمز العملة للتحليل:\n\n"
                "مثال:\n"
                "BTC"

            )

            return



        if data == "back_main":


            await query.edit_message_text(

                "🏠 القائمة الرئيسية",

                reply_markup=main_menu_keyboard()

            )



    async def receive_symbol(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):


        symbol = (
            update.message.text
            .strip()
            .upper()
        )



        school = context.user_data.get(
            "analysis_school"
        )



        if not school:


            await update.message.reply_text(

                "❌ اختر مدرسة التحليل أولاً"

            )

            return



        await update.message.reply_text(
            "⏳ جاري جلب البيانات والتحليل..."
        )



        try:


            candles = await self.crypto_api.get_klines(

                symbol,

                interval="4h",

                limit=100

            )



            if not candles:


                await update.message.reply_text(

                    "❌ لا توجد بيانات لهذه العملة"

                )

                return




            result = None



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



            elif school == "analysis_tvl":


                tvl_data = await self.crypto_api.get_tvl(
                    symbol
                )


                result = tvl.analyze(
                    tvl_data
                )





            if not result:


                await update.message.reply_text(

                    "❌ لم يتم إنشاء نتيجة"

                )

                return




            message = (

                f"📊 نتيجة التحليل\n\n"

                f"🪙 العملة: {symbol}\n"

                f"🏫 المدرسة: {result.get('school','')}\n\n"

                f"🎯 الإشارة:\n"
                f"{result.get('signal')}\n\n"

                f"{result.get('message')}\n"

            )



            # إضافة تفاصيل إضافية إن وجدت

            if "rsi" in result:

                message += (
                    f"\n📊 RSI: {result['rsi']}"
                )


            if "support" in result:

                message += (
                    f"\n\n📉 دعم: "
                    f"{result['support']}"
                    f"\n📈 مقاومة: "
                    f"{result['resistance']}"
                )


            if "volume_ratio" in result:

                message += (
                    f"\n\n🐋 قوة الحجم: "
                    f"{result['volume_ratio']}x"
                )


            await update.message.reply_text(
                message
            )



        except Exception as e:


            logger.error(
                f"Analysis error: {e}"
            )


            await update.message.reply_text(

                "❌ حدث خطأ أثناء التحليل"

            )
