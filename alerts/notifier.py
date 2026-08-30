from typing import List
from telegram import Bot
from config import TELEGRAM_BOT_TOKEN

async def send_alert_to_subscribers(bot: Bot, message: str, subscriber_ids: List[int]):
    """إرسال تنبيه فقط للمشتركين النشطين"""
    for user_id in subscriber_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message, parse_mode="HTML")
        except Exception:
            continue
