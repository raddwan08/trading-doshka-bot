from telegram import Update
from telegram.ext import ContextTypes
from utils.keyboards import analysis_keyboard
import logging

logger = logging.getLogger(name)

class AnalysisHandler:
def init(self, db, crypto_api):
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
f"💵 السعر: $`{data['current_price']:,.2f}\n"
f"📊 التغير 24س: {data['price_change_24h']:.2f}%"
)
await update.message.reply_text(message, parse_mode='Markdown')
else:
await update.message.reply_text(f"❌ لم يتم العثور على {symbol}")

async def technical_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
if not context.args:
await update.message.reply_text("❌ استخدم: /technical BTC")
return

symbol = context.args[0].upper()
data = await self.crypto_api.get_coin_data(symbol)

if data:
message = (
f"📊 التحليل الفني - {symbol}\n\n"
f"💵 السعر: `${data['current_price']:,.2f}\n"
f"📈 التغير: {data['price_change_24h']:.2f}%"
)
await update.message.reply_text(message, parse_mode='Markdown')

async def onchain_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
if not context.args:
await update.message.reply_text("❌ استخدم: /onchain BTC")
return

symbol = context.args[0].upper()
await update.message.reply_text(f"⛓️ تحليل {symbol} قريباً...")

async def show_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = update.effective_user.id

if not self.db.check_subscription(user_id):
await update.message.reply_text("🔒 للمشتركين فقط! /subscribe")
return

await update.message.reply_text("🎯 لا توجد إشارات حالياً")

async def get_coin_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
data = await self.crypto_api.get_coin_data(symbol)

if data:
message = (
f"💰 {data['name']} ({data['symbol']})\n\n"
f"💵 السعر: latex
{data['current_price']:,.2f}\n" f"📊 القيمة: 

{data['market_cap']:,.0f}"
)
await update.message.reply_text(message, parse_mode='Markdown')
