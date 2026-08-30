import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from sqlalchemy import select

from config import TELEGRAM_BOT_TOKEN, ADMIN_IDS, SUBSCRIPTION_PLANS
from database.models import init_db, AsyncSessionLocal, User
from market.coingecko import get_coin_data, search_coin
from utils.helpers import run_all_analyses
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == user.id))
        db_user = result.scalar_one_or_none()
        if not db_user:
            db_user = User(telegram_id=user.id, username=user.username)
            session.add(db_user)
            await session.commit()

    text = (
        "مرحباً بك في بوت التحليل الفني للعملات الرقمية\n\n"
        "الأوامر المتاحة:\n"
        "/analyze <رمز> - تحليل متعدد المدارس\n"
        "/plans - عرض باقات الاشتراك\n"
        "/status - حالة اشتراكك\n"
    )
    await update.message.reply_text(text)

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "باقات الاشتراك:\n\n"
    for key, plan in SUBSCRIPTION_PLANS.items():
        text += f"• {key}: ${plan['price_usd']} لمدة {plan['days']} يوم\n"
    text += "\n(نظام الدفع غير مفعل في هذه النسخة التعليمية)"
    await update.message.reply_text(text)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        db_user = result.scalar_one_or_none()
        if db_user and db_user.is_active():
            await update.message.reply_text(
                f"اشتراكك نشط حتى: {db_user.subscription_end.strftime('%Y-%m-%d')}\n"
                f"الباقة: {db_user.plan}"
            )
        else:
            await update.message.reply_text("ليس لديك اشتراك نشط.")

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("استخدم: /analyze bitcoin")
        return

    query = context.args[0].lower()
    await update.message.reply_text(f"جاري تحليل {query}...")

    coins = await search_coin(query)
    if not coins:
        await update.message.reply_text("لم يتم العثور على العملة.")
        return

    coin_id = coins[0]["id"]
    data = await get_coin_data(coin_id)
    if not data:
        await update.message.reply_text("فشل جلب البيانات.")
        return

    # بيانات مؤقتة للتوضيح (لاحقاً يمكن ربطها بشارت حقيقي)
    prices = [data["market_data"]["current_price"]["usd"]] * 100
    df = pd.DataFrame({
        "close": prices,
        "high": [p * 1.01 for p in prices],
        "low": [p * 0.99 for p in prices],
        "volume": [1000] * 100
    })

    results = run_all_analyses(df, query.upper())

    text = f"<b>تحليل {query.upper()}</b>\n\n"
    for r in results:
        text += f"<b>{r['school']}</b>\n"
        text += f"الإشارة: {r['signal']}\n"
        if r.get("reasons"):
            text += "الأسباب: " + " | ".join(r["reasons"]) + "\n"
        text += f"السعر: {r.get('last_price', 'N/A')}\n\n"

    await update.message.reply_text(text, parse_mode="HTML")

async def main():
    await init_db()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("analyze", analyze))

    logger.info("Bot started...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
