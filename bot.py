import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


from config import (
    BOT_TOKEN,
    SCHOOLS,
    COINS,
    TIMEFRAMES,
    MARKETS
)

from market.binance import get_market_data
from analysis.engine import run_analysis
from charts.chart import create_chart


logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(
    "Doshka"
)


bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)


dp = Dispatcher()



# ======================
# MAIN MENU
# ======================

def main_menu():

    kb = InlineKeyboardBuilder()

    kb.button(
        text="📊 التحليل الفني",
        callback_data="analysis"
    )

    kb.button(
        text="⚡ Futures",
        callback_data="future"
    )

    kb.button(
        text="💰 Spot",
        callback_data="spot"
    )

    kb.button(
        text="🔔 التنبيهات",
        callback_data="alerts"
    )

    kb.button(
        text="💎 الاشتراك",
        callback_data="subscribe"
    )

    kb.adjust(1)

    return kb.as_markup()



# ======================
# START
# ======================


@dp.message(Command("start"))
async def start(
    message: Message
):

    await message.answer(
        """
🌟 <b>Doshka Trading Pro</b>

نظام تحليل العملات الرقمية

📊 مدارس تحليل متعددة
⚡ Spot & Futures
🔔 تنبيهات دخول وخروج

اختر الخدمة:
""",
        reply_markup=main_menu()
    )



# ======================
# SELECT MARKET
# ======================


@dp.callback_query(
    F.data.in_(
        [
            "spot",
            "future"
        ]
    )
)
async def market_select(
    callback: CallbackQuery
):

    market = callback.data


    kb = InlineKeyboardBuilder()


    for key,value in SCHOOLS.items():

        kb.button(
            text=value["name"],
            callback_data=f"school:{market}:{key}"
        )


    kb.adjust(1)


    await callback.message.edit_text(
        f"""
📈 السوق:

<b>{MARKETS[market]['name']}</b>

اختر مدرسة التحليل:
""",
        reply_markup=kb.as_markup()
    )


    await callback.answer()




# ======================
# SCHOOL
# ======================


@dp.callback_query(
    F.data.startswith("school:")
)
async def select_school(
    callback: CallbackQuery
):

    _,market,school = callback.data.split(":")


    kb = InlineKeyboardBuilder()


    for tf in TIMEFRAMES:

        kb.button(
            text=f"⏱ {tf}",
            callback_data=
            f"tf:{market}:{school}:{tf}"
        )


    kb.adjust(2)


    await callback.message.edit_text(
        f"""
{SCHOOLS[school]['name']}

اختر الفترة الزمنية:
""",
        reply_markup=kb.as_markup()
    )

    await callback.answer()




# ======================
# TIMEFRAME
# ======================


@dp.callback_query(
    F.data.startswith("tf:")
)
async def select_timeframe(
    callback: CallbackQuery
):

    _,market,school,tf = callback.data.split(":")


    kb = InlineKeyboardBuilder()


    for coin in COINS:

        kb.button(
            text=f"💰 {coin}",
            callback_data=
            f"analyze:{market}:{school}:{tf}:{coin}"
        )


    kb.adjust(2)


    await callback.message.edit_text(
        """
اختر العملة:
""",
        reply_markup=kb.as_markup()
    )

    await callback.answer()




# ======================
# ANALYSIS
# ======================


@dp.callback_query(
    F.data.startswith("analyze:")
)
async def analysis(
    callback: CallbackQuery
):

    await callback.answer(
        "⏳ جاري التحليل..."
    )


    _,market,school,tf,coin = (
        callback.data.split(":")
    )


    await callback.message.answer(
        f"""
🔎 تحليل:

<b>{coin}USDT</b>

السوق:
{market}

المدرسة:
{SCHOOLS[school]['name']}

الفترة:
{tf}
"""
    )



    try:

        data = await get_market_data(
            coin,
            tf
        )


        result = await run_analysis(
            school,
            data,
            coin
        )


        chart = create_chart(
            data,
            result,
            coin,
            school
        )


        await callback.message.answer_photo(
            BufferedInputFile(
                chart.getvalue(),
                filename="chart.png"
            ),
            caption=result["text"]
        )


    except Exception as e:

        logger.exception(e)

        await callback.message.answer(
            "❌ حدث خطأ أثناء التحليل"
        )





# ======================
# SUBSCRIBE
# ======================


@dp.callback_query(
    F.data=="subscribe"
)
async def subscribe(
    callback:CallbackQuery
):

    await callback.message.edit_text(
        """
💎 الاشتراكات

Basic
Professional
VIP Futures

سيتم إضافة نظام الدفع لاحقاً.
"""
    )

    await callback.answer()



# ======================
# ALERTS
# ======================


@dp.callback_query(
    F.data=="alerts"
)
async def alerts(
    callback:CallbackQuery
):

    await callback.message.edit_text(
        """
🔔 نظام التنبيهات

متاح للمشتركين:

✅ دخول صفقة
✅ خروج
✅ تغير اتجاه
✅ كسر دعم
✅ كسر مقاومة
✅ مشاكل العقود Futures

"""
    )

    await callback.answer()



# ======================
# RUN
# ======================


async def main():

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    await dp.start_polling(
        bot
    )



if __name__=="__main__":

    asyncio.run(main())
