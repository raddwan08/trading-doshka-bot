from telegram import Update
from telegram.ext import ContextTypes
from utils.keyboards import main_menu_keyboard


class StartHandler:
    def __init__(self, db):
        self.db = db

    async def start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        user = update.effective_user

        self.db.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        message = (
            f"👋 أهلاً {user.first_name}!\n\n"
            "🤖 بوت التحليل الشامل للعملات الرقمية\n\n"
            "📊 التحليل: /analysis\n"
            "💰 الأسعار: /price\n"
            "🔔 التنبيهات: /alerts\n"
            "💳 الدفع: /payment\n"
            "ℹ️ المساعدة: /help"
        )

        await update.message.reply_text(
            message,
            reply_markup=main_menu_keyboard()
        )

    async def help(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        help_text = (
            "📚 الأوامر المتاحة:\n\n"
            "📊 /analysis - التحليل\n"
            "💰 /price - أسعار العملات\n"
            "🔔 /alerts - التنبيهات\n"
            "💳 /payment - الدفع\n"
            "ℹ️ /help - المساعدة\n\n"
            "💡 يمكنك أيضاً إرسال رمز عملة مباشرة مثل:\n"
            "BTC أو ETH أو SOL"
        )

        await update.message.reply_text(help_text)
