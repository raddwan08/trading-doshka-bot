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
                "🔔 التنبيهات",
                callback_data="alerts_menu"
            ),

            InlineKeyboardButton(
                "💳 الاشتراك",
                callback_data="subscribe_menu"
            )
        ],

        [
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
