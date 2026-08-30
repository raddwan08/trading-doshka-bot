import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import aiohttp
import pandas as pd
from typing import Dict, List, Optional

from models import Base, User, Payment, AnalysisHistory
from config import *
from analysis.price_action import PriceActionAnalyzer
from analysis.smc import SMCAnalyzer
from analysis.wyckoff import WyckoffAnalyzer
from analysis.ichimoku import IchimokuAnalyzer
from analysis.fibonacci import FibonacciAnalyzer
from payments.crypto_payments import CryptoPaymentProcessor

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Initialize payment processor
payment_processor = CryptoPaymentProcessor()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ==================== Helper Functions ====================

async def get_user(telegram_id: int, session: AsyncSession) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()

async def check_subscription(user_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        user = await get_user(user_id, session)
        if user and user.is_active():
            return True
        return False

async def fetch_coin_data(coin_id: str) -> Optional[Dict]:
    """جلب بيانات العملة من CoinGecko"""
    url = f"{COINGECKO_API}/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": "30",
        "interval": "daily"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                
                # تحويل البيانات إلى DataFrame
                prices = data.get("prices", [])
                volumes = data.get("total_volumes", [])
                
                df = pd.DataFrame({
                    'timestamp': [p[0] for p in prices],
                    'close': [p[1] for p in prices],
                    'volume': [v[1] for v in volumes]
                })
                
                # إضافة high و low (تقريبي)
                df['high'] = df['close'] * 1.02
                df['low'] = df['close'] * 0.98
                df['open'] = df['close'].shift(1).fillna(df['close'])
                
                return df
            return None

async def search_coin(query: str) -> List[Dict]:
    """البحث عن عملة"""
    url = f"{COINGECKO_API}/search"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params={"query": query}) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("coins", [])[:5]
            return []

# ==================== Bot Handlers ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    
    async with AsyncSessionLocal() as session:
        db_user = await get_user(user.id, session)
        if not db_user:
            db_user = User(telegram_id=user.id, username=user.username)
            session.add(db_user)
            await session.commit()
    
    keyboard = [
        [InlineKeyboardButton("📊 تحليل عملة", callback_data="analyze_menu")],
        [InlineKeyboardButton("💎 الباقات والاشتراك", callback_data="plans_menu")],
        [InlineKeyboardButton("📈 حالتي", callback_data="status_menu")],
        [InlineKeyboardButton("ℹ️ المساعدة", callback_data="help_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
<b>مرحباً {user.first_name}! 👋</b>

أنا بوت التحليل الفني المتكامل للعملات الرقمية.

<b>المميزات:</b>
• 6 مدارس تحليل فني مختلفة
• تحليلات مستقلة لكل مدرسة
• نسبة ثقة لكل تحليل
• دعم فني مستمر

<b>اختر من القائمة:</b>
"""
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze command handler"""
    user_id = update.effective_user.id
    
    # Check subscription
    if not await check_subscription(user_id):
        keyboard = [[InlineKeyboardButton("💎 الاشتراك", callback_data="plans_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ <b>هذه الميزة للمشتركين فقط</b>\n\nاشترك الآن للوصول إلى جميع التحليلات!",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return
    
    if not context.args:
        await update.message.reply_text("استخدم: /analyze bitcoin")
        return
    
    query = context.args[0].lower()
    loading_msg = await update.message.reply_text(f"🔄 جاري تحليل {query.upper()}...")
    
    # Search for coin
    coins = await search_coin(query)
    if not coins:
        await loading_msg.edit_text("❌ لم يتم العثور على العملة")
        return
    
    coin_id = coins[0]["id"]
    coin_symbol = coins[0]["symbol"].upper()
    
    # Fetch data
    df = await fetch_coin_data(coin_id)
    if df is None or df.empty:
        await loading_msg.edit_text("❌ فشل جلب البيانات")
        return
    
    # Run all analyzers
    analyzers = [
        PriceActionAnalyzer(df),
        SMCAnalyzer(df),
        WyckoffAnalyzer(df),
        IchimokuAnalyzer(df),
        FibonacciAnalyzer(df)
    ]
    
    analyses = []
    for analyzer in analyzers:
        try:
            result = analyzer.analyze()
            analyses.append(result)
        except Exception as e:
            logger.error(f"Error in {analyzer.__class__.__name__}: {e}")
    
    # Build response
    current_price = df['close'].iloc[-1]
    response = f"<b>📊 تحليل {coin_symbol}</b>\n"
    response += f"💰 السعر الحالي: ${current_price:.4f}\n\n"
    
    # Summary of signals
    buy_signals = [a for a in analyses if a['signal'] == 'شراء']
    sell_signals = [a for a in analyses if a['signal'] == 'بيع']
    neutral_signals = [a for a in analyses if a['signal'] == 'محايد']
    
    response += f"<b>ملخص الإشارات:</b>\n"
    response += f"🟢 شراء: {len(buy_signals)}\n"
    response += f"🔴 بيع: {len(sell_signals)}\n"
    response += f"⚪ محايد: {len(neutral_signals)}\n\n"
    
    # Detailed analysis
    for analysis in analyses:
        response += f"<b>{'='*30}</b>\n"
        response += f"<b>🏫 {analysis['school']}</b>\n"
        signal_emoji = "🟢" if analysis['signal'] == "شراء" else "🔴" if analysis['signal'] == "بيع" else "⚪"
        response += f"{signal_emoji} الإشارة: <b>{analysis['signal']}</b>\n"
        response += f"📊 الثقة: {analysis['confidence']}%\n"
        
        if 'details' in analysis:
            response += f"📝 <b>التفاصيل:</b>\n"
            for detail in analysis['details'][:3]:
                response += f"• {detail}\n"
        response += "\n"
    
    # Save analysis history
    async with AsyncSessionLocal() as session:
        history = AnalysisHistory(
            user_id=user_id,
            coin_symbol=coin_symbol,
            analysis_result=response
        )
        session.add(history)
        await session.commit()
    
    await loading_msg.edit_text(response, parse_mode="HTML")

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Plans command handler"""
    keyboard = [
        [InlineKeyboardButton("💎 شهر - $20", callback_data="buy_1_month")],
        [InlineKeyboardButton("💎 3 شهور - $50", callback_data="buy_3_months")],
        [InlineKeyboardButton("💎 6 شهور - $90", callback_data="buy_6_months")],
        [InlineKeyboardButton("💎 12 شهر - $150", callback_data="buy_12_months")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    plans_text = """
<b>💎 باقات الاشتراك</b>

اختر الباقة المناسبة لك:

<b>شهر واحد - $20</b>
• تحليل كامل
• جميع المدارس الست
• تنبيهات فورية

<b>3 شهور - $50</b>
• كل مميزات الشهر
• أولوية في الدعم
• توفير 17%

<b>6 شهور - $90</b>
• كل مميزات 3 شهور
• تحليلات حصرية
• توفير 25%

<b>12 شهر - $150</b>
• كل المميزات
• خصم خاص
• توفير 37%
"""
    await update.message.reply_text(plans_text, reply_markup=reply_markup, parse_mode="HTML")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Status command handler"""
    user_id = update.effective_user.id
    
    async with AsyncSessionLocal() as session:
        user = await get_user(user_id, session)
        
        if user and user.is_active():
            remaining = user.subscription_end - datetime.utcnow()
            days_left = remaining.days
            
            status_text = f"""
<b>📈 حالة اشتراكك</b>

✅ <b>نشط</b>
📅 الباقة: {user.plan}
⏰ الأيام المتبقية: {days_left} يوم
📆 تاريخ الانتهاء: {user.subscription_end.strftime('%Y-%m-%d')}
"""
        else:
            status_text = """
<b>📈 حالة اشتراكك</b>

❌ <b>غير نشط</b>
ليس لديك اشتراك حالي.

اشترك الآن للوصول إلى:
• 6 مدارس تحليل فني
• تحليلات مستقلة
• نسبة ثقة لكل تحليل
"""
            keyboard = [[InlineKeyboardButton("💎 اشترك الآن", callback_data="plans_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(status_text, reply_markup=reply_markup, parse_mode="HTML")
            return
    
    await update.message.reply_text(status_text, parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = query.from_user.id
    
    if callback_data == "analyze_menu":
        await query.message.reply_text(
            "📊 استخدم الأمر:\n/analyze bitcoin\n\nلتحليل أي عملة تريدها"
        )
    
    elif callback_data == "plans_menu":
        await plans_command(update, context)
    
    elif callback_data == "status_menu":
        await status_command(update, context)
    
    elif callback_data == "help_menu":
        help_text = """
<b>ℹ️ المساعدة</b>

<b>الأوامر المتاحة:</b>
• /start - البداية
• /analyze [عملة] - تحليل عملة
• /plans - الباقات
• /status - حالة الاشتراك

<b>مدارس التحليل:</b>
1. Price Action
2. SMC
3. Wyckoff
4. Ichimoku
5. Fibonacci

<b>للدفع:</b>
USDT (TRC20) أو BTC أو ETH

<b>للدعم:</b>
@YourSupportUsername
"""
        await query.message.reply_text(help_text, parse_mode="HTML")
    
    elif callback_data.startswith("buy_"):
        plan_key = callback_data.replace("buy_", "")
        plan_info = SUBSCRIPTION_PLANS.get(plan_key)
        
        if plan_info:
            payment_keyboard = [
                [InlineKeyboardButton("💵 USDT (TRC20)", callback_data=f"pay_usdt_{plan_key}")],
                [InlineKeyboardButton("₿ Bitcoin", callback_data=f"pay_btc_{plan_key}")],
                [InlineKeyboardButton("Ξ Ethereum", callback_data=f"pay_eth_{plan_key}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="plans_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(payment_keyboard)
            
            payment_text = f"""
<b>💳 الدفع لخطة {plan_key}</b>

المبلغ: ${plan_info['price_usd']}
المدة: {plan_info['days']} يوم

<b>اختر طريقة الدفع:</b>
"""
            await query.message.reply_text(payment_text, reply_markup=reply_markup, parse_mode="HTML")
    
    elif callback_data.startswith("pay_"):
        parts = callback_data.split("_")
        currency = parts[1].upper()
        plan_key = "_".join(parts[2:])
        plan_info = SUBSCRIPTION_PLANS.get(plan_key)
        
        if plan_info:
            # Generate payment request
            payment = payment_processor.generate_payment_request(
                user_id=user_id,
                amount_usd=plan_info['price_usd'],
                currency=currency,
                plan=plan_key
            )
            
            crypto_amount = payment_processor.calculate_crypto_amount(
                plan_info['price_usd'],
                currency
            )
            
            payment_text = f"""
<b>📤 أرسل المبلغ إلى العنوان التالي:</b>

العملة: <b>{currency}</b>
المبلغ: <b>{crypto_amount} {currency}</b>
العنوان: <code>{payment['wallet_address']}</code>

<b>معرف الدفع:</b> <code>{payment['payment_id']}</code>

⚠️ <b>مهم:</b>
1. أرسل المبلغ المحدد بالضبط
2. بعد الإرسال، أرسل transaction hash هنا
3. سيتم تفعيل اشتراكك بعد التأكيد

<b>لإرسال الـ hash:</b>
/confirm [transaction_hash]
"""
            await query.message.reply_text(payment_text, parse_mode="HTML")
    
    elif callback_data == "back_main":
        await start(update, context)

async def confirm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm payment command"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "استخدم: /confirm [transaction_hash]\nمثال: /confirm 0x123456789abcdef"
        )
        return
    
    transaction_hash = context.args[0]
    
    # Here you would verify the transaction
    # For now, just confirm it
    async with AsyncSessionLocal() as session:
        # Find pending payment
        result = await session.execute(
            select(Payment).where(
                Payment.user_id == user_id,
                Payment.status == "pending"
            )
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            await update.message.reply_text("❌ لا يوجد دفع معلق")
            return
        
        # Update payment status
        payment.status = "confirmed"
        payment.transaction_hash = transaction_hash
        payment.confirmed_at = datetime.utcnow()
        
        # Activate subscription
        user = await get_user(user_id, session)
        if user:
            plan_info = SUBSCRIPTION_PLANS.get(payment.plan)
            if plan_info:
                user.is_subscribed = True
                user.plan = payment.plan
                if user.subscription_end and user.subscription_end > datetime.utcnow():
                    user.subscription_end += timedelta(days=plan_info['days'])
                else:
                    user.subscription_end = datetime.utcnow() + timedelta(days=plan_info['days'])
        
        await session.commit()
    
    await update.message.reply_text(
        "✅ <b>تم تفعيل اشتراكك بنجاح!</b>\n\nيمكنك الآن استخدام جميع ميزات البوت.",
        parse_mode="HTML"
    )

 def main():
    """Main function"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set!")
        return
    
    # Initialize database
    asyncio.run(init_db())
    
    # Create application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("plans", plans_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("confirm", confirm_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("Bot started successfully...")
    await app.run_polling()

if __name__ == "__main__":
    main()
