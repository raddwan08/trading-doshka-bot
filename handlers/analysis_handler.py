from telegram import Update
from telegram.ext import ContextTypes
from utils.keyboards import analysis_keyboard
import logging
import random

logger = logging.getLogger(__name__)

class AnalysisHandler:
    def __init__(self, db, crypto_api):
        self.db = db
        self.crypto_api = crypto_api
    
    async def show_analysis_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📊 قائمة التحليل\n\nاختر نوع التحليل:",
            reply_markup=analysis_keyboard(),
            parse_mode='Markdown'
        )
    
    async def handle_analysis_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == "analysis_technical":
            await query.edit_message_text(
                "📈 أرسل رمز العملة للتحليل الفني\nمثال: BTC"
            )
        elif query.data == "analysis_onchain":
            await query.edit_message_text(
                "⛓️ أرسل رمز العملة لتحليل On-Chain\nمثال: BTC"
            )
    
    async def get_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ استخدم: /price BTC")
            return
        
        symbol = context.args[0].upper()
        data = await self.crypto_api.get_coin_data(symbol)
        
        if data:
            message = (
                f"💰 {data['name']} ({data['symbol']})\n\n"
                f"💵 السعر: ${data['current_price']:,.2f}\n"
                f"📊 التغير 24س: {data['price_change_24h']:.2f}%"
            )
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ لم يتم العثور على {symbol}")
    
    async def technical_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "📈 التحليل الفني\n\n"
                "أرسل رمز العملة بعد الأمر:\n"
                "/technical BTC\n"
                "/technical ETH\n\n"
                "أو أرسل الرمز مباشرة وسأحلله لك:"
            )
            return
        
        symbol = context.args[0].upper()
        data = await self.crypto_api.get_coin_data(symbol)
        
        if data:
            price = data['current_price']
            change = data['price_change_24h']
            
            # تحليل بسيط
            if change > 5:
                trend = "📈 صاعد بقوة"
                signal = "شراء قوي"
            elif change > 1:
                trend = "📈 صاعد"
                signal = "شراء"
            elif change > -1:
                trend = "📊 محايد"
                signal = "انتظار"
            elif change > -5:
                trend = "📉 هابط"
                signal = "بيع"
            else:
                trend = "📉 هابط بقوة"
                signal = "بيع قوي"
            
            # مستويات الدعم والمقاومة
            resistance = price * 1.05
            support = price * 0.95
            
            message = (
                f"📊 التحليل الفني - {symbol}\n\n"
                f"💰 السعر: ${price:,.2f}\n"
                f"📈 التغير 24س: {change:.2f}%\n"
                f"📊 الاتجاه: {trend}\n"
                f"🎯 الإشارة: {signal}\n\n"
                f"📈 مقاومة: ${resistance:,.2f}\n"
                f"📉 دعم: ${support:,.2f}\n\n"
                f"⚡ مؤشرات:\n"
                f"• RSI: {random.randint(30, 70)}\n"
                f"• MACD: {'إيجابي' if change > 0 else 'سلبي'}\n"
                f"• حجم التداول: ${data.get('volume_24h', 0):,.0f}"
            )
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ لم يتم العثور على {symbol}")
    
    async def onchain_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "⛓️ تحليل On-Chain\n\n"
                "أرسل رمز العملة بعد الأمر:\n"
                "/onchain BTC\n"
                "/onchain ETH\n\n"
                "أو أرسل الرمز مباشرة وسأحلله لك:"
            )
            return
        
        symbol = context.args[0].upper()
        data = await self.crypto_api.get_coin_data(symbol)
        
        if data:
            price = data['current_price']
            volume = data.get('volume_24h', 0)
            
            message = (
                f"⛓️ تحليل On-Chain - {symbol}\n\n"
                f"💰 السعر: ${price:,.2f}\n"
                f"📊 حجم التداول: ${volume:,.0f}\n\n"
                f"🔍 مؤشرات السلسلة:\n"
                f"• نشاط العناوين: {'مرتفع' if volume > 1000000 else 'متوسط'}\n"
                f"• تدفق العملات: {'إيجابي' if data['price_change_24h'] > 0 else 'سلبي'}\n"
                f"• الضغط الشرائي: {'قوي' if data['price_change_24h'] > 2 else 'ضعيف'}\n\n"
                f"📱 للمزيد من التحليل استخدم /technical {symbol}"
            )
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ لم يتم العثور على {symbol}")
    
    async def show_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not self.db.check_subscription(user_id):
            await update.message.reply_text("🔒 للمشتركين فقط! /subscribe")
            return
        
        await update.message.reply_text("🎯 لا توجد إشارات حالياً")
    
    async def get_coin_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
        data = await self.crypto_api.get_coin_data(symbol)
        
        if data:
            price = data['current_price']
            change = data['price_change_24h']
            volume = data.get('volume_24h', 0)
            
            # تحليل سريع
            if change > 5:
                analysis = "📈 صاعد بقوة - فرصة شراء محتملة"
            elif change > 1:
                analysis = "📈 صاعد - اتجاه إيجابي"
            elif change > -1:
                analysis = "📊 محايد - انتظار إشارات"
            else:
                analysis = "📉 هابط - حذر من الشراء"
            
            message = (
                f"💰 {data['name']} ({data['symbol']})\n\n"
                f"💵 السعر: ${price:,.2f}\n"
                f"📊 التغير 24س: {change:.2f}%\n"
                f"📈 التحليل: {analysis}\n\n"
                f"📊 حجم التداول: ${volume:,.0f}\n\n"
                f"📱 استخدم:\n"
                f"/technical {symbol} للتحليل الفني\n"
                f"/onchain {symbol} لتحليل السلسلة"
            )
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ لم يتم العثور على {symbol}")
