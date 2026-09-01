from telegram import Update
from telegram.ext import ContextTypes

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


        data = query.data



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



        if data in schools:


            context.user_data[
                "analysis_school"
            ] = data



            await query.edit_message_text(

                f"{schools[data]}\n\n"
                "🪙 أرسل رمز العملة:\n\n"
                "مثال:\n"
                "BTC"

            )

            return



        if data == "back_main":


            context.user_data.clear()


            await query.edit_message_text(

                "🏠 القائمة الرئيسية",

                reply_markup=main_menu_keyboard()

            )



    async def receive_symbol(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):


        user_id = update.effective_user.id



        # فحص الاشتراك

        if not self.db.check_subscription(
            user_id
        ):

            await update.message.reply_text(

                "🔒 هذه الخدمة للمشتركين فقط\n\n"
                "استخدم /subscribe للاشتراك"

            )

            return



        school = context.user_data.get(
            "analysis_school"
        )



        if not school:


            await update.message.reply_text(

                "❌ اختر مدرسة التحليل أولاً"

            )

            return



        symbol = (

            update.message.text
            .strip()
            .upper()

        )



        await update.message.reply_text(

            "⏳ جاري تحليل "
            f"{symbol} ..."

        )



        try:


            result = None



            # TVL له مصدر مختلف

            if school == "analysis_tvl":


                tvl_data = await self.crypto_api.get_tvl(
                    symbol
                )


                result = tvl.analyze(
                    tvl_data
                )


            else:


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

                    "❌ لم يتم إنشاء تحليل"

                )

                return



            message = (

                "📊 Doshka Trading Pro\n\n"

                f"🪙 العملة: {symbol}\n"

                f"🏫 المدرسة: "
                f"{result.get('school','')}\n\n"

                f"🎯 الإشارة: "
                f"{result.get('signal','WAIT')}\n\n"

                f"{result.get('message','')}"

            )



            # تفاصيل إضافية

            if "rsi" in result:

                message += (

                    f"\n\n📊 RSI: "
                    f"{result['rsi']}"

                )


            if "support" in result:

                message += (

                    f"\n📉 الدعم: "
                    f"{result['support']}"

                    f"\n📈 المقاومة: "
                    f"{result['resistance']}"

                )


            if "volume_ratio" in result:

                message += (

                    f"\n🐋 قوة الحجم: "
                    f"{result['volume_ratio']}x"

                )


            if "pattern" in result and result["pattern"]:

                message += (

                    f"\n🦋 النموذج: "
                    f"{result['pattern']}"

                )



            await update.message.reply_text(
                message
            )


            # تنظيف الاختيار بعد التحليل

            context.user_data.pop(
                "analysis_school",
                None
            )



        except Exception as e:


            logger.error(
                f"Analysis error: {e}"
            )


            await update.message.reply_text(

                "❌ حدث خطأ أثناء التحليل"

            )
