from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import SUBSCRIPTION_PLANS

class SubscriptionHandler:
def init(self, db):
self.db = db

async def show_plans(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
message = (
"💎 خطط الاشتراك\n\n"
"📅 شهري: 25 USDT\n"
"📅 3 أشهر: 60 USDT\n"
"📅 6 أشهر: 100 USDT\n"
"👑 سنوي: 180 USDT\n\n"
"للدفع: /payment"
)

keyboard = [
[InlineKeyboardButton("💳 ادفع الآن", callback_data="subscribe_now")]
]

await update.message.reply_text(
message,
reply_markup=InlineKeyboardMarkup(keyboard),
parse_mode='Markdown'
)

async def handle_subscription_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()

if query.data == "subscribe_now":
await query.edit_message_text(
"اختر الشبكة للدفع: /payment"
)
