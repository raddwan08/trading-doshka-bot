from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import WALLETS
import logging

logger = logging.getLogger(__name__)

class PaymentHandler:
    def __init__(self, db, application=None, blockchain_verifier=None):
        self.db = db
        self.application = application
        self.blockchain_verifier = blockchain_verifier
    
    async def show_payment_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = (
            "💳 طرق الدفع\n\n"
            "نقبل USDT على:\n"
            "1️⃣ Solana\n"
            "2️⃣ Ethereum\n"
            "3️⃣ BSC"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🔷 Solana", callback_data="payment_sol"),
                InlineKeyboardButton("🔶 Ethereum", callback_data="payment_eth")
            ],
            [
                InlineKeyboardButton("🟡 BSC", callback_data="payment_bsc")
            ]
        ]
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def handle_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        network = query.data.replace("payment_", "").upper()
        wallet = WALLETS.get(network)
        
        if wallet:
            message = (
                f"💳 الدفع عبر {network}\n\n"
                f"أرسل USDT إلى:\n{wallet}\n\n"
                f"بعد التحويل أرسل:\n"
                f"/verify TRANSACTION_HASH"
            )
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown'
            )
    
    async def verify_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ استخدم: /verify TRANSACTION_HASH")
            return
        
        tx_hash = context.args[0]
        await update.message.reply_text("⏳ جاري التحقق من المعاملة...")
