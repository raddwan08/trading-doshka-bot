import asyncio, logging
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BufferedInputFile, CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    BOT_TOKEN, ADMIN_ID, SQLITE_PATH, PLANS, NETWORKS, COINS, SCHOOLS,
    PAYMENT_SCAN_SECONDS, ORDER_TTL_MINUTES
)
from database.db import Database
from market import klines
from analysis.engine import FUNCS
from payments.manager import find_payment
from chart import make_chart

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log=logging.getLogger("doshka")

bot=Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp=Dispatcher(storage=MemoryStorage())
db=Database(SQLITE_PATH)

class States(StatesGroup):
    custom=State()

def main_kb():
    b=InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📊 التحليل الفني",callback_data="start_analysis"))
    b.row(InlineKeyboardButton(text="💎 الاشتراكات",callback_data="plans"))
    b.row(InlineKeyboardButton(text="ℹ️ مساعدة",callback_data="help"),
          InlineKeyboardButton(text="📋 حالتي",callback_data="status"))
    return b.as_markup()

def schools_kb():
    b=InlineKeyboardBuilder()
    for k,v in SCHOOLS.items():
        b.row(InlineKeyboardButton(text=f"{v['emoji']} {v['name']}",callback_data=f"school:{k}"))
    b.row(InlineKeyboardButton(text="🔙",callback_data="back"))
    return b.as_markup()

def tf_kb(school):
    b=InlineKeyboardBuilder()
    for tf in SCHOOLS[school]["timeframes"]:
        b.row(InlineKeyboardButton(text=f"⏰ {tf}",callback_data=f"tf:{school}:{tf}"))
    b.row(InlineKeyboardButton(text="🔙",callback_data="start_analysis"))
    return b.as_markup()

def coins_kb(school,tf):
    b=InlineKeyboardBuilder()
    for i in range(0,len(COINS),2):
        row=[InlineKeyboardButton(text=f"💰 {x}",callback_data=f"an:{school}:{tf}:{x}") for x in COINS[i:i+2]]
        b.row(*row)
    b.row(InlineKeyboardButton(text="🔍 عملة أخرى",callback_data=f"custom:{school}:{tf}"))
    b.row(InlineKeyboardButton(text="🔙",callback_data=f"school:{school}"))
    return b.as_markup()

def plans_kb():
    b=InlineKeyboardBuilder()
    for k,p in PLANS.items():
        b.row(InlineKeyboardButton(text=f"{p.emoji} {p.name} — {p.price:g} USDT",callback_data=f"sub:{k}"))
    b.row(InlineKeyboardButton(text="🔙",callback_data="back"))
    return b.as_markup()

def networks_kb(plan):
    b=InlineKeyboardBuilder()
    for n in ("sol","eth","bnb"):
        b.row(InlineKeyboardButton(text=f"💵 USDT — {NETWORKS[n]['name']}",callback_data=f"net:{plan}:{n}"))
    b.row(InlineKeyboardButton(text="🔙",callback_data="plans"))
    return b.as_markup()

def pay_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 فحص الآن",callback_data="check")],
        [InlineKeyboardButton(text="🔙 الاشتراكات",callback_data="plans")],
    ])

async def ensure_user(m):
    await db.upsert_user(m.from_user.id, m.from_user.username)

@dp.message(Command("start"))
async def start(m:Message):
    await ensure_user(m)
    await m.answer(
        "🌟 <b>Doshka Trading Pro</b>\n\n"
        "📊 تحليل متعدد المدارس\n💵 اشتراك USDT متعدد الشبكات\n"
        "🔎 التحقق من الدفع تلقائيًا\n\nاختر:",
        reply_markup=main_kb()
    )

@dp.callback_query(F.data=="back")
async def back(c:CallbackQuery):
    await c.message.edit_text("🌟 <b>Doshka Trading Pro</b>",reply_markup=main_kb())
    await c.answer()

@dp.callback_query(F.data=="start_analysis")
async def start_analysis(c:CallbackQuery):
    if not await db.active(c.from_user.id,ADMIN_ID):
        await c.answer("❌ التحليل متاح للمشتركين فقط.",show_alert=True); return
    await c.message.edit_text("📊 <b>اختر مدرسة التحليل:</b>",reply_markup=schools_kb())
    await c.answer()

@dp.callback_query(F.data.startswith("school:"))
async def school(c:CallbackQuery):
    s=c.data.split(":",1)[1]
    if s not in SCHOOLS:
        await c.answer("اختيار غير صالح",show_alert=True); return
    await c.message.edit_text(
        f"{SCHOOLS[s]['emoji']} <b>{SCHOOLS[s]['name']}</b>\nاختر الإطار الزمني:",
        reply_markup=tf_kb(s)
    )
    await c.answer()

@dp.callback_query(F.data.startswith("tf:"))
async def timeframe(c:CallbackQuery):
    _,s,t=c.data.split(":",2)
    if s not in SCHOOLS or t not in SCHOOLS[s]["timeframes"]:
        await c.answer("اختيار غير صالح",show_alert=True); return
    await c.message.edit_text("💰 <b>اختر العملة:</b>",reply_markup=coins_kb(s,t))
    await c.answer()

@dp.callback_query(F.data.startswith("custom:"))
async def custom(c:CallbackQuery,state:FSMContext):
    _,s,t=c.data.split(":",2)
    await state.update_data(school=s,tf=t)
    await state.set_state(States.custom)
    await c.message.edit_text("🔍 أرسل رمز العملة مثل BTC أو ETH")
    await c.answer()

@dp.message(StateFilter(States.custom))
async def custom_message(m:Message,state:FSMContext):
    data=await state.get_data()
    await state.clear()
    symbol=(m.text or "").upper().replace("USDT","").strip()
    if not symbol.isalnum():
        await m.answer("❌ رمز العملة غير صالح.",reply_markup=main_kb()); return
    await do_analysis(m,symbol,data["school"],data["tf"])

@dp.callback_query(F.data.startswith("an:"))
async def analyze(c:CallbackQuery):
    _,s,t,x=c.data.split(":",3)
    await c.answer("⏳ جاري التحليل...")
    await do_analysis(c.message,x,s,t)

async def do_analysis(m,symbol,school,tf):
    if not await db.active(m.chat.id,ADMIN_ID):
        await m.answer("❌ الاشتراك غير نشط.",reply_markup=main_kb()); return
    if school not in FUNCS:
        await m.answer("❌ مدرسة غير صالحة."); return
    msg=await m.answer("⏳ جاري جلب بيانات السوق وتحليلها...")
    data=await klines(symbol,tf)
    if len(data)<80:
        await msg.edit_text(
            "❌ لم تصل بيانات كافية من Binance لهذه العملة/الفترة.\n"
            "جرّب رمزًا مدعومًا مثل BTC أو ETH."
        ); return
    try:
        sig=FUNCS[school](data,symbol)
        chart=make_chart(data[-120:],sig,f"{symbol}/USDT — {SCHOOLS[school]['name']}")
        await msg.delete()
        await m.answer_photo(
            BufferedInputFile(chart.read(),filename=f"{symbol}_{school}.png"),
            caption=sig["analysis"],
            reply_markup=main_kb()
        )
    except Exception:
        log.exception("analysis failed")
        await msg.edit_text("❌ حدث خطأ أثناء التحليل. أعد المحاولة بعد لحظات.")

@dp.callback_query(F.data=="plans")
async def plans(c:CallbackQuery):
    await c.message.edit_text("💎 <b>الاشتراكات — USDT فقط</b>\n\nاختر الباقة:",reply_markup=plans_kb())
    await c.answer()

@dp.callback_query(F.data.startswith("sub:"))
async def subscription(c:CallbackQuery):
    p=c.data.split(":",1)[1]
    if p not in PLANS:
        await c.answer("باقة غير صالحة",show_alert=True); return
    plan=PLANS[p]
    await c.message.edit_text(
        f"💳 <b>{plan.name}</b>\n💵 {plan.price:g} USDT\n\nاختر الشبكة:",
        reply_markup=networks_kb(p)
    )
    await c.answer()

@dp.callback_query(F.data.startswith("net:"))
async def network(c:CallbackQuery):
    _,p,n=c.data.split(":",2)
    if p not in PLANS or n not in NETWORKS:
        await c.answer("اختيار غير صالح",show_alert=True); return
    order_id,created,expires=await db.create_order(c.from_user.id,p,n,ORDER_TTL_MINUTES)
    wallet=NETWORKS[n]["wallet"]
    await c.message.edit_text(
        f"💳 <b>طلب الدفع #{order_id}</b>\n\n"
        f"📦 {PLANS[p].name}\n💵 <b>{PLANS[p].price:g} USDT</b>\n"
        f"🌐 {NETWORKS[n]['name']}\n\n"
        f"📮 أرسل USDT إلى:\n<code>{wallet}</code>\n\n"
        f"⏱ صلاحية الطلب: {ORDER_TTL_MINUTES} دقيقة.\n"
        "لا ترسل TX Hash؛ البوت يبحث عن التحويل تلقائيًا.\n\n"
        "⚠️ يجب إرسال USDT على الشبكة المحددة فقط.",
        reply_markup=pay_kb()
    )
    await c.answer()

async def check_order(order, user_id):
    if order["user_id"] != user_id: return None
    found=await find_payment(order)
    if not found: return None
    claimed=await db.claim_transaction(order["network"],found["tx_id"],user_id,order["id"],found["amount"])
    if not claimed: return None
    expires=await db.activate(user_id,order["plan"])
    return found,expires

@dp.callback_query(F.data=="check")
async def check(c:CallbackQuery):
    order=await db.pending(c.from_user.id)
    if not order:
        await c.answer("لا يوجد طلب دفع نشط.",show_alert=True); return
    await c.answer("🔎 أفحص الشبكة الآن...")
    result=await check_order(order,c.from_user.id)
    if not result:
        await c.message.answer(
            "❌ لم يتم العثور بعد على تحويل USDT مطابق للمبلغ والشبكة ووقت الطلب.\n"
            "تأكد من أن التحويل مؤكد وأنك أرسلت USDT إلى العنوان الصحيح."
        )
        return
    found,expires=result
    await c.message.answer(
        f"🎉 <b>تم تأكيد الدفع وتفعيل الاشتراك!</b>\n\n"
        f"📦 {PLANS[order['plan']].name}\n"
        f"💵 {found['amount']:.6f} USDT\n"
        f"🌐 {NETWORKS[order['network']]['name']}\n"
        f"📅 ينتهي: {expires.strftime('%Y-%m-%d %H:%M UTC')}",
        reply_markup=main_kb()
    )

@dp.callback_query(F.data=="status")
async def status(c:CallbackQuery):
    r=await db.status(c.from_user.id)
    if not r or not r["is_active"]:
        text="❌ <b>لا يوجد اشتراك نشط.</b>"
    else:
        text=f"✅ <b>اشتراك نشط</b>\n\n📦 {PLANS.get(r['plan'],PLANS['1m']).name}\n📅 ينتهي: {r['expire_date']}"
    await c.message.edit_text(text,reply_markup=main_kb())
    await c.answer()

@dp.callback_query(F.data=="help")
async def help_(c:CallbackQuery):
    await c.message.edit_text(
        "📖 <b>المدارس</b>\n\n"
        "📊 وايكوف — سلوك السعر والحجم ومناطق التجميع/التوزيع\n"
        "🌊 إليوت — بنية القمم والقيعان\n"
        "🦋 هارمونيك — نسب XABCD\n"
        "📈 كلاسيكي — EMA/RSI/MACD وتوافق الإشارات\n"
        "🐋 الحيتان — شذوذ الحجم واتجاه الشموع ذات الحجم المرتفع\n"
        "🔒 السيولة — مشاركة الحجم، وليست TVL on-chain حقيقيًا\n\n"
        "💵 الدفع: USDT على Solana / Ethereum / BNB Smart Chain.\n"
        "⚠️ التحليل تعليمي/آلي وليس ضمانًا للربح.",
        reply_markup=main_kb()
    )
    await c.answer()

async def payment_monitor():
    while True:
        try:
            await db.expire_old_orders()
            for order in await db.pending_batch():
                try:
                    result=await check_order(order,order["user_id"])
                    if result:
                        found,expires=result
                        await bot.send_message(
                            order["user_id"],
                            f"🎉 <b>تم تأكيد الدفع تلقائيًا!</b>\n"
                            f"📦 {PLANS[order['plan']].name}\n"
                            f"💵 {found['amount']:.6f} USDT\n"
                            f"🌐 {NETWORKS[order['network']]['name']}\n"
                            f"📅 ينتهي: {expires.strftime('%Y-%m-%d %H:%M UTC')}",
                            reply_markup=main_kb()
                        )
                except Exception:
                    log.exception("payment order %s",order.get("id"))
        except Exception:
            log.exception("payment monitor")
        await asyncio.sleep(PAYMENT_SCAN_SECONDS)

async def main():
    await db.init(ADMIN_ID)
    monitor=asyncio.create_task(payment_monitor())
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        monitor.cancel()
        await bot.session.close()

if __name__=="__main__":
    asyncio.run(main())
