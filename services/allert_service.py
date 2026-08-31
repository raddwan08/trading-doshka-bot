from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(name)

class AlertService:
def init(self, application, db, crypto_api):
self.application = application
self.db = db
self.crypto_api = crypto_api

async def show_alert_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
message = "🔔 التنبيهات\n\nاختر نوع التنبيه:"

keyboard = [
[InlineKeyboardButton("💰 تنبيه السعر", callback_data="alert_price")]
]

await update.message.reply_text(
message,
reply_markup=InlineKeyboardMarkup(keyboard),
parse_mode='Markdown'
)

async def handle_alert_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()

if query.data == "alert_price":
await query.edit_message_text(
"💰 أرسل رمز العملة والسعر\nمثال: BTC 50000"
)

async def show_my_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = update.effective_user.id
alerts = self.db.get_user_alerts(user_id)

if not alerts:
await update.message.reply_text("📭 لا توجد تنبيهات")
return

message = "🔔 تنبيهاتك:\n\n"
for alert in alerts:
message += f"• {alert.symbol}\n"

await update.message.reply_text(message, parse_mode='Markdown')

async def delete_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text("استخدم /myalerts لعرض التنبيهات")
