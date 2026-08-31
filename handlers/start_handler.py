from telegram import Update
from telegram.ext import ContextTypes
from utils.keyboards import main_menu_keyboard

class StartHandler:
    def __init__(self, db):
        self.db = db
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        self.db.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        is_premium = self.db.check_subscription(user.id)
        
        if is_premium:
            message = f"👋 أهلاً {user.first_name}!\n\n✅ اشتراكك نشط"
        else:
            message = (
                f"👋 أهلاً {user.first_name}!\n\n"
                f"🤖 بوت التحليل الشامل للعملات الرقمية\n\n"
                f"💎 للاشتراك: /subscribe\n"
                f"📊 للتحليل: /analysis"
            )
        
        await update.message.reply_text(
            message,
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "📚 الأوامر:\n\n"
            "/analysis - التحليل\n"
            "/price - الأسعار\n"
            "/subscribe - الاشتراك\n"
            "/payment - الدفع\n"
            "/alerts - التنبيهات"
        )
        await update.message.reply_text(help_text)
