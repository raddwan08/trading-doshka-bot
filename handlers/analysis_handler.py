import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from utils.keyboards import analysis_keyboard, main_menu_keyboard
from analysis import wyckoff, harmonic, classic, whales, tvl

logger = logging.getLogger(name)

WAITING_SYMBOL = 1

class AnalysisHandler:
def init(self, db, crypto_api):
self.db = db
self.crypto_api = crypto_api

async def show_analysis_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    await message.reply_text(
        "📊 مدارس التحليل\n\nاختر مدرسة التحليل:",
        reply_markup=analysis_keyboard()
    )

async def handle_analysis_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query is None:
        return ConversationHandler.END

    await query.answer()

    data = query.data

    schools = {
        "analysis_wyckoff": "📈 تحليل وايكوف",
        "analysis_harmonic": "🦋 تحليل هارمونيك",
        "analysis_classic": "📉 التحليل الكلاسيكي",
        "analysis_whales": "🐋 تحليل الحيتان",
        "analysis_tvl": "🔒 تحليل TVL",
    }

    if data in schools:
        context.user_data["analysis_school"] = data

        await query.edit_message_text(
            f"{schools[data]}\n\n"
            "🪙 أرسل رمز العملة للتحليل:\n\n"
            "مثال: BTC"
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

async def receive_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return WAITING_SYMBOL

    school = context.user_data.get("analysis_school")

    if school is None:
        await update.message.reply_text(
            "❌ لم يتم اختيار مدرسة التحليل.",
            reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END

    symbol = update.message.text.strip().upper()
    symbol = symbol.replace("USDT", "")
    symbol = symbol.replace("/", "")
    symbol = symbol.replace(" ", "")

    if not symbol:
        await update.message.reply_text("❌ أرسل رمز عملة صحيحاً مثل BTC")
        return WAITING_SYMBOL

    await update.message.reply_text(
        f"⏳ جاري تحليل {symbol}..."
    )

    try:
        result = None

        if school == "analysis_tvl":
            tvl_data = await self.crypto_api.get_tvl(symbol)
            result = tvl.analyze(tvl_data)

        else:
            candles = await self.crypto_api.get_klines(
                symbol,
                interval="4h",
                limit=100
            )

            if not candles:
                await update.message.reply_text(
                    f"❌ لا توجد بيانات للعملة {symbol}"
                )
                return ConversationHandler.END

            if school == "analysis_wyckoff":
                result = wyckoff.analyze(candles)

            elif school == "analysis_harmonic":
                result = harmonic.analyze(candles)

            elif school == "analysis_classic":
                result = classic.analyze(candles)

            elif school == "analysis_whales":
                result = whales.analyze(candles)

        if not result:
            await update.message.reply_text(
                "❌ فشل إنشاء التحليل."
            )
            return ConversationHandler.END

        message = (
            "📊 Doshka Trading Pro\n\n"
            f"🪙 العملة: {symbol}\n"
            f"🏫 المدرسة: {result.get('school', '')}\n\n"
            f"🎯 الإشارة: {result.get('signal', 'WAIT')}\n\n"
            f"{result.get('message', '')}"
        )

        if result.get("rsi") is not None:
            message += f"\n\n📊 RSI: {result['rsi']}"

        if result.get("support") is not None:
            message += f"\n📉 الدعم: {result['support']}"

        if result.get("resistance") is not None:
            message += f"\n📈 المقاومة: {result['resistance']}"

        if result.get("volume_ratio") is not None:
            message += f"\n🐋 قوة الحجم: {result['volume_ratio']}x"

        if result.get("pattern"):
            message += f"\n🦋 النموذج: {result['pattern']}"

        await update.message.reply_text(message)

        context.user_data.pop("analysis_school", None)

        return ConversationHandler.END

    except Exception:
        logger.exception("Analysis error")

        await update.message.reply_text(
            "❌ حدث خطأ أثناء تنفيذ التحليل."
        )

        context.user_data.pop("analysis_school", None)

        return ConversationHandler.END
