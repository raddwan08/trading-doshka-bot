handlers/analysis_handler.py

import logging

from telegram import Update
from telegram.ext import (
ContextTypes,
ConversationHandler
)

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

logger = logging.getLogger(name)

حالة انتظار رمز العملة

WAITING_SYMBOL = 1

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

    message = update.effective_message

    await message.reply_text(
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


    # اختيار مدرسة التحليل
    if data in schools:

        context.user_data["analysis_school"] = data

        await query.edit_message_text(
            f"{schools[data]}\n\n"
            "🪙 أرسل رمز العملة للتحليل:\n\n"
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


    # العودة إلى القائمة الرئيسية
    if data == "back_main":

        context.user_data.clear()

        await query.edit_message_text(
            "🏠 القائمة الرئيسية\n\n"
            "اختر الخدمة:",
            reply_markup=main_menu_keyboard()
        )

        return ConversationHandler.END


    return ConversationHandler.END


async def receive_symbol(
    self,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    # =========================
    # التحليل مجاني
    # لا يوجد فحص اشتراك هنا
    # =========================

    school = context.user_data.get(
        "analysis_school"
    )


    if not school:

        await update.message.reply_text(
            "❌ لم يتم اختيار مدرسة التحليل.\n\n"
            "اضغط على 📊 التحليل واختر المدرسة أولاً.",
            reply_markup=main_menu_keyboard()
        )

        return ConversationHandler.END


    symbol = (
        update.message.text
        .strip()
        .upper()
    )


    # تنظيف الإدخال
    symbol = symbol.replace("/", "")
    symbol = symbol.replace("USDT", "")


    # التحقق من وجود رمز
    if not symbol or len(symbol) > 15:

        await update.message.reply_text(
            "❌ رمز العملة غير صحيح.\n\n"
            "مثال صحيح:\n"
            "BTC\n"
            "ETH\n"
            "SOL"
        )

        return WAITING_SYMBOL


    await update.message.reply_text(
        f"⏳ جاري تحليل {symbol}..."
    )


    try:

        result = None


        # =========================
        # تحليل TVL
        # =========================

        if school == "analysis_tvl":

            tvl_data = await self.crypto_api.get_tvl(
                symbol
            )

            result = tvl.analyze(
                tvl_data
            )


        # =========================
        # التحليلات التي تحتاج شموع
        # =========================

        else:

            candles = await self.crypto_api.get_klines(
                symbol,
                interval="4h",
                limit=100
            )


            if not candles:

                await update.message.reply_text(
                    f"❌ لم أستطع العثور على بيانات لـ {symbol}.\n\n"
                    "تأكد من أن رمز العملة صحيح."
                )

                return ConversationHandler.END


            # وايكوف
            if school == "analysis_wyckoff":

                result = wyckoff.analyze(
                    candles
                )


            # هارمونيك
            elif school == "analysis_harmonic":

                result = harmonic.analyze(
                    candles
                )


            # كلاسيكي
            elif school == "analysis_classic":

                result = classic.analyze(
                    candles
                )


            # الحيتان
            elif school == "analysis_whales":

                result = whales.analyze(
                    candles
                )


        # =========================
        # التحقق من النتيجة
        # =========================

        if not result:

            await update.message.reply_text(
                "❌ فشل إنشاء التحليل."
            )

            return ConversationHandler.END


        # =========================
        # إنشاء التقرير
        # =========================

        school_name = result.get(
            "school",
            ""
        )


        signal = result.get(
            "signal",
            "WAIT"
        )


        analysis_message = result.get(
            "message",
            ""
        )


        message = (

            "📊 Doshka Trading Pro\n\n"

            f"🪙 العملة: {symbol}\n"

            f"🏫 المدرسة: {school_name}\n\n"

            f"🎯 الإشارة: {signal}\n\n"

            f"{analysis_message}"

        )


        # =========================
        # RSI
        # =========================

        if "rsi" in result:

            message += (
                f"\n\n📊 RSI: "
                f"{result['rsi']}"
            )


        # =========================
        # الدعم والمقاومة
        # =========================

        if "support" in result:

            message += (
                f"\n\n📉 الدعم: "
                f"{result['support']}"
            )


        if "resistance" in result:

            message += (
                f"\n📈 المقاومة: "
                f"{result['resistance']}"
            )


        # =========================
        # الحجم
        # =========================

        if "volume_ratio" in result:

            message += (
                f"\n🐋 قوة الحجم: "
                f"{result['volume_ratio']}x"
            )


        # =========================
        # النموذج
        # =========================

        if (
            "pattern" in result
            and result["pattern"]
        ):

            message += (
                f"\n🦋 النموذج: "
                f"{result['pattern']}"
            )


        # =========================
        # TVL
        # =========================

        if "tvl" in result:

            message += (
                f"\n\n🔒 TVL: "
                f"${result['tvl']:,.0f}"
            )


        if "change_30d" in result:

            message += (
                f"\n📊 تغير 30 يوم: "
                f"{result['change_30d']:.2f}%"
            )


        await update.message.reply_text(
            message
        )


        # تنظيف حالة التحليل
        context.user_data.pop(
            "analysis_school",
            None
        )


        return ConversationHandler.END


    except Exception:

        logger.exception(
            "Analysis error"
        )


        await update.message.reply_text(
            "❌ حدث خطأ أثناء التحليل.\n"
            "حاول مرة أخرى لاحقاً."
        )


        context.user_data.pop(
            "analysis_school",
            None
        )


        return ConversationHandler.END
