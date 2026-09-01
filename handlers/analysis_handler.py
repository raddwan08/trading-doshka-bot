from telegram import Update
from telegram.ext import ContextTypes

from utils.keyboards import analysis_keyboard

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


    def __init__(self, db, crypto_api):

        self.db = db
        self.crypto_api = crypto_api



    async def show_analysis_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        await update.message.reply_text(

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

        await query.answer()



        schools = {

            "analysis_wyckoff":
                "📈 وايكوف",

            "analysis_harmonic":
                "🦋 هارمونيك",

            "analysis_classic":
                "📉 كلاسيكي",

            "analysis_whales":
                "🐋 الحيتان",

            "analysis_tvl":
                "🔒 TVL"

        }



        if query.data in schools:


            context.user_data[
                "selected_school"
            ] = query.data



            await query.edit_message_text(

                f"{schools[query.data]}\n\n"
                "أرسل رمز العملة:\n"
                "مثال: BTC"

            )



    async def receive_symbol(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):


        symbol = update.message.text.upper()


        school = context.user_data.get(
            "selected_school"
        )


        if not school:

            await update.message.reply_text(

                "❌ اختر مدرسة التحليل أولاً"

            )

            return



        await update.message.reply_text(
            "⏳ جاري التحليل..."
        )



        candles = await self.crypto_api.get_klines(

            symbol,

            interval="4h",

            limit=100

        )



        if not candles:

            await update.message.reply_text(

                "❌ لم أستطع جلب بيانات العملة"

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




        if result:


            message = (

                f"📊 نتيجة التحليل\n\n"

                f"🪙 العملة: {symbol}\n\n"

                f"🎯 الإشارة: "
                f"{result.get('signal')}\n\n"

                f"{result.get('message')}"

            )


            await update.message.reply_text(
                message
            )


        else:

            await update.message.reply_text(

                "❌ لم يتم إنشاء التحليل"

            )
