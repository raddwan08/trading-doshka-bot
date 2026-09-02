from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "📊 التحليل",
                callback_data="analysis_menu"
            ),

            InlineKeyboardButton(
                "💰 الأسعار",
                callback_data="prices_menu"
            )
        ],

        [
            InlineKeyboardButton(
                "🚀 Futures",
                callback_data="futures_menu"
            ),

            InlineKeyboardButton(
                "💳 الاشتراك",
                callback_data="subscribe_menu"
            )
        ],

        [
            InlineKeyboardButton(
                "🔔 التنبيهات",
                callback_data="alerts_menu"
            ),

            InlineKeyboardButton(
                "ℹ️ مساعدة",
                callback_data="help_menu"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def analysis_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "📈 وايكوف",
                callback_data="analysis_wyckoff"
            ),

            InlineKeyboardButton(
                "🦋 هارمونيك",
                callback_data="analysis_harmonic"
            )
        ],

        [
            InlineKeyboardButton(
                "📉 كلاسيكي",
                callback_data="analysis_classic"
            ),

            InlineKeyboardButton(
                "🐋 الحيتان",
                callback_data="analysis_whales"
            )
        ],

        [
            InlineKeyboardButton(
                "🔒 TVL",
                callback_data="analysis_tvl"
            )
        ],

        [
            InlineKeyboardButton(
                "❌ إلغاء",
                callback_data="analysis_cancel"
            ),

            InlineKeyboardButton(
                "🔙 رجوع",
                callback_data="back_main"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def subscription_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "📅 شهر - $20",
                callback_data="subscribe_1m"
            )
        ],

        [
            InlineKeyboardButton(
                "💎 3 أشهر - $50",
                callback_data="subscribe_3m"
            )
        ],

        [
            InlineKeyboardButton(
                "👑 6 أشهر - $75",
                callback_data="subscribe_6m"
            )
        ],

        [
            InlineKeyboardButton(
                "🏆 سنة - $125",
                callback_data="subscribe_1y"
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 رجوع",
                callback_data="back_main"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)
