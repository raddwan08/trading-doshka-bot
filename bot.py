import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from config import BOT_TOKEN, SCHOOLS, COINS
from database import Database
from analysis import run_analysis


logging.basicConfig(level=logging.INFO)


bot = Bot(BOT_TOKEN)
dp = Dispatcher()

db = Database()


def main_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 التحليل الفني",
                    callback_data="analysis"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💎 الاشتراك",
                    callback_data="subscribe"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 حالتي",
                    callback_data="status"
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ المساعدة",
                    callback_data="help"
                )
            ]
        ]
    )



def schools_keyboard():

    buttons=[]

    for key,value in SCHOOLS.items():

        buttons.append(
            [
                InlineKeyboardButton(
                    text=value["name"],
                    callback_data=f"school:{key}"
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )



def coins_keyboard(school):

    buttons=[]

    for coin in COINS:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=coin,
                    callback_data=f"coin:{school}:{coin}"
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )



@dp.message(Command("start"))
async def start(message:Message):

    db.add_user(
        message.from_user.id,
        message.from_user.username
    )


    await message.answer(
        """
🌟 <b>Doshka Trading Pro</b>

بوت تحليل العملات الرقمية

اختر الخدمة:
        """,
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )



@dp.callback_query(F.data=="analysis")
async def analysis_menu(call:CallbackQuery):

    await call.message.edit_text(
        "📊 اختر مدرسة التحليل:",
        reply_markup=schools_keyboard()
    )

    await call.answer()



@dp.callback_query(F.data.startswith("school:"))
async def select_school(call:CallbackQuery):

    school=call.data.split(":")[1]


    await call.message.edit_text(
        f"اختر العملة للتحليل\n\nالمدرسة: {SCHOOLS[school]['name']}",
        reply_markup=coins_keyboard(school)
    )

    await call.answer()



@dp.callback_query(F.data.startswith("coin:"))
async def analyze_coin(call:CallbackQuery):

    _,school,coin=call.data.split(":")


    await call.message.edit_text(
        "⏳ جاري التحليل..."
    )


    result = await run_analysis(
        coin,
        school
    )


    await call.message.answer(
        result,
        reply_markup=main_keyboard()
    )


    await call.answer()



@dp.callback_query(F.data=="status")
async def status(call:CallbackQuery):

    expire=db.status(
        call.from_user.id
    )


    if expire:

        text=f"""
✅ حسابك مفعل

ينتهي:
{expire}
"""

    else:

        text="❌ لا يوجد حساب"



    await call.message.edit_text(
        text,
        reply_markup=main_keyboard()
    )



@dp.callback_query(F.data=="subscribe")
async def subscribe(call:CallbackQuery):

    await call.message.edit_text(
        """
💎 الاشتراك

حالياً النسخة التجريبية مجانية.

سيتم إضافة الدفع لاحقاً.
        """,
        reply_markup=main_keyboard()
    )



@dp.callback_query(F.data=="help")
async def help_button(call:CallbackQuery):

    await call.message.edit_text(
        """
ℹ️ المساعدة

اختر مدرسة التحليل ثم العملة.

كل مدرسة تستخدم طريقة تحليل مختلفة.
        """,
        reply_markup=main_keyboard()
    )



async def main():

    await dp.start_polling(bot)



if __name__=="__main__":

    asyncio.run(main())
