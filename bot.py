import asyncio
import os
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

SOL_WALLET = "GXrqH3WvjSSq6vfufU39oPYKDsracPnVe7sLm2rEBniJ"
BNB_ETH_WALLET = "0xF79A1bEc46037dcA06077889F4bb1A111B67723e"

PLANS = {
    "1m": {"days": 30,  "price": 20,  "name": "شهر واحد"},
    "3m": {"days": 90,  "price": 50,  "name": "3 أشهر"},
    "6m": {"days": 180, "price": 75,  "name": "6 أشهر"},
    "1y": {"days": 365, "price": 125, "name": "سنة كاملة"},
}

os.makedirs("data", exist_ok=True)
DB_PATH = "data/subscriptions.db"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            plan TEXT,
            start_date TEXT,
            expire_date TEXT,
            is_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS used_hashes (
            tx_hash TEXT PRIMARY KEY,
            user_id INTEGER,
            plan TEXT,
            network TEXT,
            amount REAL,
            used_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan TEXT,
            network TEXT,
            tx_hash TEXT,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute("INSERT OR IGNORE INTO users (user_id, is_active, plan) VALUES (?, 1, 'admin')", (ADMIN_ID,))
    conn.commit()
    conn.close()

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def is_subscribed(user_id: int) -> bool:
    if is_admin(user_id):
        return True
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT expire_date FROM users WHERE user_id = ? AND is_active = 1", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row or not row["expire_date"]:
        return False
    return datetime.fromisoformat(row["expire_date"]) > datetime.now()

def activate_sub(user_id: int, plan: str, username: str = None, full_name: str = None):
    days = PLANS[plan]["days"]
    expire = (datetime.now() + timedelta(days=days)).isoformat()
    start = datetime.now().isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO users (user_id, username, full_name, plan, start_date, expire_date, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(user_id) DO UPDATE SET
            plan=excluded.plan, start_date=excluded.start_date,
            expire_date=excluded.expire_date, is_active=1,
            username=excluded.username, full_name=excluded.full_name
    ''', (user_id, username, full_name, plan, start, expire))
    conn.commit()
    conn.close()
    return expire[:10]

def is_hash_used(tx_hash: str) -> bool:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT 1 FROM used_hashes WHERE tx_hash = ?", (tx_hash.lower(),))
    result = bool(c.fetchone())
    conn.close()
    return result

def mark_hash(tx_hash: str, user_id: int, plan: str, network: str, amount: float = 0):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO used_hashes (tx_hash, user_id, plan, network, amount) VALUES (?, ?, ?, ?, ?)",
              (tx_hash.lower(), user_id, plan, network, amount))
    conn.commit()
    conn.close()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 الاشتراكات", callback_data="plans")],
        [InlineKeyboardButton(text="📊 تحليل On-chain", callback_data="onchain")],
        [InlineKeyboardButton(text="📋 حالة اشتراكي", callback_data="status")],
        [InlineKeyboardButton(text="ℹ️ المساعدة", callback_data="help")]
    ])
    await message.answer(
        f"مرحباً <b>{message.from_user.first_name}</b> 👋\n"
        f"بوت التحليل الاحترافي + On-chain\n\n"
        f"اختر الخدمة:",
        reply_markup=kb
    )

@dp.message(Command("help"))
@dp.callback_query(F.data == "help")
async def cmd_help(event: types.Message | types.CallbackQuery):
    text = (
        "<b>أوامر البوت:</b>\n\n"
        "/start - القائمة الرئيسية\n"
        "/plans - عرض الباقات\n"
        "/status - حالة اشتراكك\n"
        "/verify - التحقق من الدفع\n"
        "/onchain - أدوات التحليل On-chain\n"
        "/help - المساعدة"
    )
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text)
        await event.answer()
    else:
        await event.answer(text)

@dp.message(Command("status"))
@dp.callback_query(F.data == "status")
async def cmd_status(event: types.Message | types.CallbackQuery):
    user_id = event.from_user.id
    if is_admin(user_id):
        text = "✅ أنت الأدمن — وصول كامل دائم"
    elif is_subscribed(user_id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT plan, expire_date FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        text = f"✅ اشتراكك نشط\nالباقة: {PLANS.get(row['plan'], {}).get('name', row['plan'])}\nينتهي: {row['expire_date'][:10]}"
    else:
        text = "❌ ليس لديك اشتراك نشط\nاستخدم /plans للاشتراك"
    
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text)
        await event.answer()
    else:
        await event.answer(text)

@dp.message(Command("plans"))
@dp.callback_query(F.data == "plans")
async def show_plans(event: types.Message | types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="شهر - 20$", callback_data="buy_1m")],
        [InlineKeyboardButton(text="3 أشهر - 50$", callback_data="buy_3m")],
        [InlineKeyboardButton(text="6 أشهر - 75$", callback_data="buy_6m")],
        [InlineKeyboardButton(text="سنة - 125$", callback_data="buy_1y")],
    ])
    text = "<b>باقات الاشتراك:</b>\nاختر الباقة:"
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("buy_"))
async def choose_network(callback: types.CallbackQuery):
    plan = callback.data.split("_")[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Solana (SOL)", callback_data=f"pay_{plan}_sol")],
        [InlineKeyboardButton(text="BNB (BSC)", callback_data=f"pay_{plan}_bnb")],
        [InlineKeyboardButton(text="Ethereum (ETH)", callback_data=f"pay_{plan}_eth")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="plans")]
    ])
    await callback.message.edit_text(
        f"<b>باقة {PLANS[plan]['name']}</b> - {PLANS[plan]['price']}$\nاختر الشبكة:",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_"))
async def show_payment_info(callback: types.CallbackQuery):
    _, plan, network = callback.data.split("_")
    price = PLANS[plan]["price"]
    wallet = SOL_WALLET if network == "sol" else BNB_ETH_WALLET
    
    text = (
        f"<b>باقة:</b> {PLANS[plan]['name']}\n"
        f"<b>السعر:</b> {price}$\n"
        f"<b>الشبكة:</b> {network.upper()}\n\n"
        f"<b>العنوان:</b>\n<code>{wallet}</code>\n\n"
        f"أرسل المبلغ ثم استخدم الأمر:\n"
        f"<code>/verify {plan} {network} الهاش_هنا</code>"
    )
    await callback.message.edit_text(text)
    await callback.answer()

@dp.message(Command("verify"))
async def verify_payment(message: types.Message, command: CommandObject):
    if not command.args:
        await message.reply("الصيغة الصحيحة:\n<code>/verify 1m sol الهاش</code>")
        return
    
    try:
        parts = command.args.split()
        if len(parts) != 3:
            await message.reply("الصيغة: /verify الباقة الشبكة الهاش")
            return
        
        plan, network, tx_hash = parts
        plan = plan.lower()
        network = network.lower()
        tx_hash = tx_hash.strip()
        
        if plan not in PLANS or network not in ["sol", "bnb", "eth"]:
            await message.reply("باقة أو شبكة غير صحيحة")
            return
        
        if is_hash_used(tx_hash):
            await message.reply("❌ هذا الهاش مستخدم من قبل")
            return
        
        await message.reply("⏳ جاري التحقق...")
        
        expire = activate_sub(
            message.from_user.id,
            plan,
            message.from_user.username,
            message.from_user.full_name
        )
        mark_hash(tx_hash, message.from_user.id, plan, network)
        
        await message.reply(
            f"✅ تم تفعيل الاشتراك بنجاح!\n"
            f"الباقة: {PLANS[plan]['name']}\n"
            f"ينتهي في: {expire}"
        )
        
        await bot.send_message(
            ADMIN_ID,
            f"🔔 اشتراك جديد\n"
            f"المستخدم: {message.from_user.full_name} (@{message.from_user.username})\n"
            f"الآي دي: <code>{message.from_user.id}</code>\n"
            f"الباقة: {plan}\n"
            f"الشبكة: {network}\n"
            f"الهاش: <code>{tx_hash}</code>"
        )
        
    except Exception as e:
        await message.reply(f"حدث خطأ: {e}")

@dp.message(Command("onchain"))
@dp.callback_query(F.data == "onchain")
async def onchain_menu(event: types.Message | types.CallbackQuery):
    user_id = event.from_user.id
    if not is_subscribed(user_id):
        text = "❌ هذه الميزة للمشتركين فقط\nاستخدم /plans للاشتراك"
        if isinstance(event, types.CallbackQuery):
            await event.message.edit_text(text)
            await event.answer()
        else:
            await event.answer(text)
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="تحليل محفظة", callback_data="oc_wallet")],
        [InlineKeyboardButton(text="تتبع الحيتان", callback_data="oc_whales")],
        [InlineKeyboardButton(text="تحليل عقد", callback_data="oc_contract")],
    ])
    text = "📊 أدوات التحليل On-chain:"
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb)

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="admin_stats")],
    ])
    await message.answer("🔐 لوحة التحكم الخاصة بك:", reply_markup=kb)

@dp.message(Command("stats"))
@dp.callback_query(F.data == "admin_stats")
async def admin_stats(event: types.Message | types.CallbackQuery):
    if not is_admin(event.from_user.id):
        return
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE is_active = 1 AND plan != 'admin'")
    active = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM used_hashes")
    payments = c.fetchone()[0]
    conn.close()
    
    text = f"<b>إحصائيات البوت</b>\n\nالمشتركين النشطين: {active}\nعدد المدفوعات: {payments}"
    
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text)
        await event.answer()
    else:
        await event.answer(text)

@dp.message(Command("give"))
async def give_sub(message: types.Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    if not command.args:
        await message.reply("الصيغة: /give user_id الباقة\nمثال: /give 123456789 1m")
        return
    try:
        uid, plan = command.args.split()
        uid = int(uid)
        if plan not in PLANS:
            await message.reply("باقة غير صحيحة")
            return
        expire = activate_sub(uid, plan)
        await message.reply(f"✅ تم إعطاء {plan} للمستخدم {uid}\nينتهي: {expire}")
        try:
            await bot.send_message(uid, f"تم تفعيل اشتراك {PLANS[plan]['name']} لك من قبل الأدمن")
        except:
            pass
    except:
        await message.reply("خطأ في الصيغة")

async def main():
    init_db()
    print("البوت يعمل الآن...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
