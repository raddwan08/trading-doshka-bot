from telegram import Update
from telegram.ext import ContextTypes
from utils.keyboards import analysis_keyboard
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
            "📊 قائمة التحليل\n\nاختر مدرسة التحليل:",
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
            "analysis_wyckoff": "📈 وايكوف",
            "analysis_harmonic": "🦋 هارمونيك",
            "analysis_classic": "📉 كلاسيكي",
            "analysis_whales": "🐋 الحيتان",
            "analysis_tvl": "🔒 TVL"
        }


        if query.data in schools:

            context.user_data["analysis_school"] = query.data

            await query.edit_message_text(
                f"{schools[query.data]}\n\n"
                "أرسل رمز العملة للتحليل\n\n"
                "مثال:\n"
                "BTC"
            )

            return


        if query.data == "back_main":

            from utils.keyboards import main_menu_keyboard

            await query.edit_message_text(
                "🏠 القائمة الرئيسية",
                reply_markup=main_menu_keyboard()
            )


    async def analyze_symbol(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        if not context.args:

            await update.message.reply_text(
                "❌ أرسل رمز العملة\nمثال:\nBTC"
            )
            return


        symbol = context.args[0].upper()


        school = context.user_data.get(
            "analysis_school"
        )


        if not school:

            await update.message.reply_text(
                "❌ اختر مدرسة التحليل أولاً من القائمة"
            )
            return



        data = await self.crypto_api.get_coin_data(
            symbol
        )


        if not data:

            await update.message.reply_text(
                f"❌ لم يتم العثور على {symbol}"
            )
            return



        price = data["current_price"]
        change = data["price_change_24h"]
        volume = data.get(
            "volume_24h",
            0
        )



        school_name = {
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
        }.get(
            school,
            "📊 تحليل"
        )



        if change > 3:
            signal = "🟢 إيجابي"
        elif change < -3:
            signal = "🔴 سلبي"
        else:
            signal = "🟡 محايد"



        message = (

            f"{school_name}\n\n"

            f"🪙 العملة: {symbol}\n"

            f"💰 السعر: ${price:,.2f}\n"

            f"📊 تغير 24 ساعة: {change:.2f}%\n"

            f"📦 الحجم: ${volume:,.0f}\n\n"

            f"🎯 الإشارة الحالية: {signal}\n\n"

            "⚠️ هذا الإصدار هو الهيكل الأساسي.\n"
            "سيتم ربطه بمحرك المدرسة الخاص بها."
        )


        await update.message.reply_text(
            message
        )



    async def get_price(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        if not context.args:

            await update.message.reply_text(
                "❌ استخدم:\n/price BTC"
            )
            return


        symbol = context.args[0].upper()

        data = await self.crypto_api.get_coin_data(
            symbol
        )


        if data:

            await update.message.reply_text(

                f"💰 {data['name']}\n\n"
                f"السعر: ${data['current_price']:,.2f}\n"
                f"التغير: {data['price_change_24h']:.2f}%"

            )

        else:

            await update.message.reply_text(
                "❌ العملة غير موجودة"
            )
