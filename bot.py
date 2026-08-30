import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from sqlalchemy import Column, Integer, String, DateTime, Boolean, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os
import aiohttp
import pandas as pd

load_dotenv()

# ====================== Config ======================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

SUBSCRIPTION_PLANS = {
    "1_month": {"days": 30, "price_usd": 20},
    "3_months": {"days": 90, "price_usd": 50},
    "6_months": {"days": 180, "price_usd": 90},
    "12_months": {"days": 365, "price_usd": 150},
}

# ====================== Database ======================
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    is_subscribed = Column(Boolean, default=False)
    subscription_end = Column(DateTime, nullable=True)
    plan = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def is_active(self) -> bool:
        if not self.is_subscribed or not self.subscription_end:
            return False
        return self.subscription_end > datetime.utcnow()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ====================== Market ======================
async def search_coin(query: str):
    url = "https://api.coingecko.com/api/v3/search"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params={"query": query}) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("coins", [])[:5]
            return []

async def get_coin_data(coin_id: str):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    params = {"localization": "false", "tickers": "false", "market_data": "true",
              "community_data": "false", "developer_data": "false", "sparkline": "false"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            return None

# ====================== Analysis (مبسطة) ======================
def simple_analysis(price: float, symbol: str):
    return [
        {"school": "Price Action", "signal": "neutral", "reasons": ["تحليل أساسي"], "last_price": price},
        {"school": "SMC", "signal": "neutral", "reasons": ["تحليل أساسي"], "last_price": price},
        {"school": "Wyckoff", "signal": "neutral", "reasons": ["تحليل أساسي"], "last_price": price},
    ]

# ====================== Bot Handlers ======================
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
        "مرحباً بك في بوت التحليل الفني\n\n"
        "الأوامر:\n"
        "/analyze <اسم العملة> - مثال: /analyze bitcoin\n"
        "/plans - باقات الاشتراك\n"
        "/status - حالة اشتراكك"
    )
    await update.message.reply_text(text)

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "باقات الاشتراك:\n\n"
    for key, plan in SUBSCRIPTION_PLANS.items():
        text += f"• {key}: ${plan['price_usd']} لمدة {plan['days']} يوم\n"
    text += "\n(نظام الدفع غير مفعل حالياً)"
    await update.message.reply_text(text)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        db_user = result.scalar_one_or_none()
        if db_user and db_user.is_active():
            await update.message.reply_text(
                f"اشتراكك نشط حتى: {db_user.subscription_end.strftime('%Y-%m-%d')}\nالباقة: {db_user.plan}"
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

    price = data["market_data"]["current_price"]["usd"]
    results = simple_analysis(price, query.upper())

    text = f"<b>تحليل {query.upper()}</b>\nالسعر الحالي: ${price}\n\n"
    for r in results:
        text += f"<b>{r['school']}</b>\nالإشارة: {r['signal']}\n\n"

    await update.message.reply_text(text, parse_mode="HTML")

async def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN غير موجود!")
        return

    await init_db()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("analyze", analyze))

    logger.info("Bot started successfully...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
