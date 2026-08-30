
from __future__ import annotations

import asyncio
import logging
import re

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from analysis.engine import FUNCS
from chart import make_chart
from config import (
    ADMIN_ID,
    COINS,
    NETWORKS,
    ORDER_TTL_MINUTES,
    PAYMENT_SCAN_SECONDS,
    PLANS,
    SCHOOLS,
    BOT_TOKEN,
    SQLITE_PATH,
    validate_public_config,
)
from database.db import Database
from market import klines
from payments.manager import find_payment


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("doshka")

validate_public_config()

bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=MemoryStorage())
db = Database(SQLITE_PATH)


class States(StatesGroup):
    custom = State()


def main_kb():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📊 التحليل الفني", callback_data="start_analysis"))
    b.row(InlineKeyboardButton(text="💎 الاشتراكات", callback_data="plans"))
    b.row(
        InlineKeyboardButton(text="ℹ️ مساعدة", callback_data="help"),
        InlineKeyboardButton(text="📋 حالتي", callback_data="status"),
    )
    return b.as_markup()


def schools_kb():
    b = InlineKeyboardBuilder()
    for key, school in SCHOOLS.items():
        b.row(
            InlineKeyboardButton(
                text=f"{school['emoji']} {school['name']}",
                callback_data=f"school:{key}",
            )
        )
    b.row(InlineKeyboardButton(text="🔙", callback_data="back"))
    return b.as_markup()


def tf_kb(school):
    b = InlineKeyboardBuilder()
    for tf in SCHOOLS[school]["timeframes"]:
        b.row(
            InlineKeyboardButton(
                text=f"⏰ {tf}",
                callback_data=f"tf:{school}:{tf}",
            )
        )
    b.row(InlineKeyboardButton(text="🔙", callback_data="start_analysis"))
    return b.as_markup()


def coins_kb(school, tf):
    b = InlineKeyboardBuilder()
    for i in range(0, len(COINS), 2):
        row = [
            InlineKeyboardButton(
                text=f"💰 {coin}",
                callback_data=f"an:{school}:{tf}:{coin}",
            )
            for coin in COINS[i : i + 2]
        ]
        b.row(*row)
    b.row(
        InlineKeyboardButton(
            text="🔍 عملة أخرى",
            callback_data=f"custom:{school}:{tf}",
        )
    )
    b.row(InlineKeyboardButton(text="🔙", callback_data=f"school:{school}"))
    return b.as_markup()


def plans_kb():
    b = InlineKeyboardBuilder()
    for key, plan in PLANS.items():
        b.row(
            InlineKeyboardButton(
                text=f"{plan.emoji} {plan.name} — {plan.price:g} USDT",
                callback_data=f"sub:{key}",
            )
        )
    b.row(InlineKeyboardButton(text="🔙", callback_data="back"))
    return b.as_markup()


def networks_kb(plan):
    b = InlineKeyboardBuilder()
    for key in ("sol", "eth", "bnb"):
        network = NETWORKS[key]
        b.row(
            InlineKeyboardButton(
                text=f"💵 USDT — {network['name']}",
                callback_data=f"net:{plan}:{key}",
            )
        )
    b.row(InlineKeyboardButton(text="🔙", callback_data="plans"))
    return b.as_markup()


def pay_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 فحص الآن", callback_data="check")],
            [InlineKeyboardButton(text="🔙 الاشتراكات", callback_data="plans")],
        ]
    )


async def ensure_user(message: Message):
    await db.upsert_user(message.from_user.id, message.from_user.username)


@dp.message(Command("start"))
async def start(message: Message):
    await ensure_user(message)
    await message.answer(
        "🌟 <b>Doshka Trading Pro</b>\n\n"
        "📊 تحليل متعدد المدارس\n"
        "💵 اشتراك USDT متعدد الشبكات\n"
        "🔎 التحقق من الدفع تلقائيًا\n\n"
        "اختر من القائمة:",
        reply_markup=main_kb(),
    )


@dp.message(Command("id"))
async def user_id(message: Message):
    await ensure_user(message)
    await message.answer(f"🆔 Telegram ID: <code>{message.from_user.id}</code>")


@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌟 <b>Doshka Trading Pro</b>\n\nاختر:",
        reply_markup=main_kb(),
    )
    await callback.answer()


@dp.callback_query(F.data == "start_analysis")
async def start_analysis(callback: CallbackQuery):
    await db.upsert_user(callback.from_user.id, callback.from_user.username)
    if not await db.active(callback.from_user.id, ADMIN_ID):
        await callback.answer("❌ التحليل متاح للمشتركين فقط.", show_alert=True)
        return
    await callback.message.edit_text(
        "📊 <b>اختر مدرسة التحليل:</b>",
        reply_markup=schools_kb(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("school:"))
async def school(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    if key not in SCHOOLS:
        await callback.answer("❌ اختيار غير صالح.", show_alert=True)
        return
    item = SCHOOLS[key]
    await callback.message.edit_text(
        f"{item['emoji']} <b>{item['name']}</b>\n\nاختر الإطار الزمني:",
        reply_markup=tf_kb(key),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("tf:"))
async def timeframe(callback: CallbackQuery):
    _, school_key, timeframe_key = callback.data.split(":", 2)
    if (
        school_key not in SCHOOLS
        or timeframe_key not in SCHOOLS[school_key]["timeframes"]
    ):
        await callback.answer("❌ اختيار غير صالح.", show_alert=True)
        return
    await callback.message.edit_text(
        "💰 <b>اختر العملة:</b>",
        reply_markup=coins_kb(school_key, timeframe_key),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("custom:"))
async def custom(callback: CallbackQuery, state: FSMContext):
    _, school_key, timeframe_key = callback.data.split(":", 2)
    if (
        school_key not in SCHOOLS
        or timeframe_key not in SCHOOLS[school_key]["timeframes"]
    ):
        await callback.answer("❌ اختيار غير صالح.", show_alert=True)
        return

    await state.update_data(school=school_key, tf=timeframe_key)
    await state.set_state(States.custom)
    await callback.message.edit_text(
        "🔍 أرسل رمز العملة فقط، مثال:\n<code>BTC</code> أو <code>ETH</code>"
    )
    await callback.answer()


@dp.message(StateFilter(States.custom))
async def custom_message(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    symbol = (message.text or "").upper().replace("USDT", "").strip()
    if not re.fullmatch(r"[A-Z0-9]{2,15}", symbol):
        await message.answer(
            "❌ رمز العملة غير صالح. استخدم حروف/أرقام فقط، مثال BTC.",
            reply_markup=main_kb(),
        )
        return

    await do_analysis(
        message,
        symbol,
        data["school"],
        data["tf"],
    )


@dp.callback_query(F.data.startswith("an:"))
async def analyze(callback: CallbackQuery):
    _, school_key, timeframe_key, symbol = callback.data.split(":", 3)
    if (
        school_key not in SCHOOLS
        or timeframe_key not in SCHOOLS[school_key]["timeframes"]
        or symbol not in COINS
    ):
        await callback.answer("❌ اختيار غير صالح.", show_alert=True)
        return

    await callback.answer("⏳ جاري التحليل...")
    await do_analysis(callback.message, symbol, school_key, timeframe_key)


async def do_analysis(message: Message, symbol: str, school_key: str, timeframe: str):
    if not await db.active(message.chat.id, ADMIN_ID):
        await message.answer("❌ الاشتراك غير نشط.", reply_markup=main_kb())
        return

    if school_key not in FUNCS:
        await message.answer("❌ مدرسة غير صالحة.")
        return

    progress = await message.answer(
        f"⏳ جاري تحليل <b>{symbol}/USDT</b> بطريقة "
        f"<b>{SCHOOLS[school_key]['name']}</b>..."
    )

    try:
        candles = await klines(symbol, timeframe, limit=300)
        if len(candles) < 80:
            await progress.edit_text(
                "❌ لم تصل بيانات كافية من Binance لهذه العملة/الفترة.\n"
                "جرّب BTC أو ETH أو إطارًا زمنيًا آخر."
            )
            return

        signal = FUNCS[school_key](candles, symbol)
        chart = make_chart(
            candles[-120:],
            signal,
            f"{symbol}/USDT — {SCHOOLS[school_key]['name']} — {timeframe}",
        )

        await progress.delete()
        await message.answer_photo(
            BufferedInputFile(
                chart.read(),
                filename=f"{symbol}_{school_key}_{timeframe}.png",
            ),
            caption=signal["analysis"],
            reply_markup=main_kb(),
        )
    except Exception:
        log.exception(
            "analysis failed: school=%s symbol=%s tf=%s",
            school_key,
            symbol,
            timeframe,
        )
        await progress.edit_text(
            "❌ تعذر تنفيذ التحليل الآن.\n"
            "تحقق من رمز العملة وحاول مرة أخرى بعد قليل."
        )


@dp.callback_query(F.data == "plans")
async def plans(callback: CallbackQuery):
    await callback.message.edit_text(
        "💎 <b>الاشتراكات — USDT فقط</b>\n\nاختر الباقة:",
        reply_markup=plans_kb(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("sub:"))
async def subscription(callback: CallbackQuery):
    plan_key = callback.data.split(":", 1)[1]
    if plan_key not in PLANS:
        await callback.answer("❌ باقة غير صالحة.", show_alert=True)
        return

    plan = PLANS[plan_key]
    await callback.message.edit_text(
        f"💳 <b>{plan.name}</b>\n"
        f"💵 <b>{plan.price:g} USDT</b>\n\n"
        "اختر الشبكة التي ستدفع عليها:",
        reply_markup=networks_kb(plan_key),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("net:"))
async def network(callback: CallbackQuery):
    _, plan_key, network_key = callback.data.split(":", 2)

    if plan_key not in PLANS or network_key not in NETWORKS:
        await callback.answer("❌ اختيار غير صالح.", show_alert=True)
        return

    network = NETWORKS[network_key]
    if not network.get("wallet"):
        await callback.answer(
            "❌ هذه الشبكة غير مهيأة في Railway. راجع متغيرات WALLET.",
            show_alert=True,
        )
        return

    order_id, _, expires = await db.create_order(
        callback.from_user.id,
        plan_key,
        network_key,
        ORDER_TTL_MINUTES,
    )

    await callback.message.edit_text(
        f"💳 <b>طلب الدفع #{order_id}</b>\n\n"
        f"📦 {PLANS[plan_key].name}\n"
        f"💵 <b>{PLANS[plan_key].price:g} USDT</b>\n"
        f"🌐 {network['name']}\n\n"
        f"📮 أرسل USDT إلى هذا العنوان:\n"
        f"<code>{network['wallet']}</code>\n\n"
        f"⏱ صلاحية الطلب: {ORDER_TTL_MINUTES} دقيقة.\n"
        "🔎 لا تحتاج إلى إرسال TX Hash؛ النظام يفحص البلوكشين تلقائيًا.\n\n"
        "⚠️ أرسل USDT على الشبكة المحددة فقط، وتأكد من العنوان قبل الإرسال.",
        reply_markup=pay_kb(),
    )
    await callback.answer()


async def check_order(order: dict, user_id: int):
    if order["user_id"] != user_id:
        return None

    found = await find_payment(order)
    if not found:
        return None

    claimed = await db.claim_transaction(
        order["network"],
        found["tx_id"],
        user_id,
        order["id"],
        found["amount"],
    )
    if not claimed:
        return None

    expires = await db.activate(user_id, order["plan"])
    return found, expires


@dp.callback_query(F.data == "check")
async def check(callback: CallbackQuery):
    order = await db.pending(callback.from_user.id)
    if not order:
        await callback.answer("لا يوجد طلب دفع نشط.", show_alert=True)
        return

    await callback.answer("🔎 أفحص الشبكة الآن...")
    try:
        result = await check_order(order, callback.from_user.id)
    except Exception:
        log.exception("manual payment check failed")
        await callback.message.answer(
            "⚠️ تعذر الاتصال بالشبكة الآن. سيستمر الفحص التلقائي."
        )
        return

    if not result:
        await callback.message.answer(
            "⏳ لم يتم العثور بعد على تحويل USDT مطابق.\n"
            "تأكد من الشبكة والعنوان والمبلغ، وانتظر تأكيد البلوكشين."
        )
        return

    found, expires = result
    await callback.message.answer(
        f"🎉 <b>تم تأكيد الدفع وتفعيل الاشتراك!</b>\n\n"
        f"📦 {PLANS[order['plan']].name}\n"
        f"💵 {found['amount']:.6f} USDT\n"
        f"🌐 {NETWORKS[order['network']]['name']}\n"
        f"🔗 <code>{found['tx_id']}</code>\n"
        f"📅 ينتهي: {expires.strftime('%Y-%m-%d %H:%M UTC')}",
        reply_markup=main_kb(),
    )


@dp.callback_query(F.data == "status")
async def status(callback: CallbackQuery):
    result = await db.status(callback.from_user.id)
    if not result or not result["is_active"]:
        text = "❌ <b>لا يوجد اشتراك نشط.</b>"
    else:
        plan = PLANS.get(result["plan"])
        text = (
            "✅ <b>اشتراك نشط</b>\n\n"
            f"📦 {plan.name if plan else result['plan']}\n"
            f"📅 ينتهي: {result['expire_date']}"
        )

    await callback.message.edit_text(text, reply_markup=main_kb())
    await callback.answer()


@dp.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "📖 <b>مدارس التحليل</b>\n\n"
        "📊 <b>وايكوف:</b> الحجم والسلوك السعري والتراكم/التصريف.\n"
        "🌊 <b>إليوت:</b> القمم والقيعان وبنية الحركة.\n"
        "🦋 <b>هارمونيك:</b> نسب XABCD والانعكاسات المحتملة.\n"
        "📈 <b>كلاسيكي:</b> EMA + RSI + MACD.\n"
        "🐋 <b>الحيتان:</b> شذوذات الحجم والشموع الكبيرة.\n"
        "🔒 <b>السيولة:</b> الحجم واتساع النطاق؛ ليست TVL on-chain.\n\n"
        "💵 الدفع: USDT على Ethereum / BNB Smart Chain / Solana.\n"
        "⚠️ التحليل آلي وتعليمي وليس ضمانًا للربح.",
        reply_markup=main_kb(),
    )
    await callback.answer()


async def payment_monitor():
    while True:
        try:
            await db.expire_old_orders()
            for order in await db.pending_batch():
                try:
                    result = await check_order(order, order["user_id"])
                    if not result:
                        continue

                    found, expires = result
                    await bot.send_message(
                        order["user_id"],
                        f"🎉 <b>تم تأكيد الدفع تلقائيًا!</b>\n\n"
                        f"📦 {PLANS[order['plan']].name}\n"
                        f"💵 {found['amount']:.6f} USDT\n"
                        f"🌐 {NETWORKS[order['network']]['name']}\n"
                        f"🔗 <code>{found['tx_id']}</code>\n"
                        f"📅 ينتهي: {expires.strftime('%Y-%m-%d %H:%M UTC')}",
                        reply_markup=main_kb(),
                    )
                except Exception:
                    log.exception("payment order failed: %s", order.get("id"))
        except Exception:
            log.exception("payment monitor failed")

        await asyncio.sleep(PAYMENT_SCAN_SECONDS)


async def main():
    await db.init(ADMIN_ID)
    monitor = asyncio.create_task(payment_monitor())
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        log.info("Doshka Trading Pro started")
        await dp.start_polling(bot)
    finally:
        monitor.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
