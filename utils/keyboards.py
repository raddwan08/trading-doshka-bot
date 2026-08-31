from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 التحليل", callback_data="analysis_menu"),
            InlineKeyboardButton("💰 الأسعار", callback_data="prices_menu")
        ],
        [
            InlineKeyboardButton("🔔 التنبيهات", callback_data="alerts_menu"),
            InlineKeyboardButton("💳 الاشتراك", callback_data="subscribe_menu")
        ],
        [
            InlineKeyboardButton("ℹ️ مساعدة", callback_data="help_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def analysis_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📈 تحليل فني", callback_data="analysis_technical"),
            InlineKeyboardButton("⛓️ On-Chain", callback_data="analysis_onchain")
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
