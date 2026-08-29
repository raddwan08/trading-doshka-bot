import asyncio
import os
import sqlite3
import aiohttp
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
    "1m":  {"days": 30,  "price": 20,  "name": "شهر واحد"},
    "3m":  {"days": 90,  "price": 50,  "name": "3 أشهر"},
    "6m":  {"days": 180, "price": 75,  "name": "6 أشهر"},
    "1y":  {"days": 365, "price": 125, "name": "سنة كاملة"},
}

os.makedirs("data", exist_ok=True)
DB_PATH = "data/subscriptions.db"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ====================== قاعدة البيانات ======================
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, plan TEXT,
        start_date TEXT, expire_date TEXT, is_active INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS used_hashes (
        tx_hash TEXT PRIMARY KEY, user_id INTEGER, plan TEXT, network TEXT,
        used_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, symbol TEXT,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, symbol))''')
    c.execute("INSERT OR IGNORE INTO users (user_id, is_active, plan) VALUES (?,1,'admin')", (ADMIN_ID,))
    conn.commit()
    conn.close()

def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID

def is_subscribed(uid: int) -> bool:
    if is_admin(uid): return True
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT expire_date FROM users WHERE user_id=? AND is_active=1", (uid,))
    row = c.fetchone()
    conn.close()
    if not row or not row["expire_date"]: return False
    return datetime.fromisoformat(row["expire_date"]) > datetime.now()

def activate_sub(uid, plan, username=None, full_name=None):
    expire = (datetime.now() + timedelta(days=PLANS[plan]["days"])).isoformat()
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT INTO users (user_id,username,full_name,plan,start_date,expire_date,is_active)
                 VALUES (?,?,?,?,?,?,1)
                 ON CONFLICT(user_id) DO UPDATE SET plan=excluded.plan, start_date=excluded.start_date,
                 expire_date=excluded.expire_date, is_active=1, username=excluded.username, full_name=excluded.full_name''',
              (uid, username, full_name, plan, datetime.now().isoformat(), expire))
    conn.commit()
    conn.close()
    return expire[:10]

def is_hash_used(tx): 
    conn = get_conn()
    res = conn.execute("SELECT 1 FROM used_hashes WHERE tx_hash=?", (tx.lower(),)).fetchone()
    conn.close()
    return bool(res)

def mark_hash(tx, uid, plan, network):
    conn = get_conn()
    conn.execute("INSERT INTO used_hashes (tx_hash,user_id,plan,network) VALUES (?,?,?,?)", (tx.lower(), uid, plan, network))
    conn.commit()
    conn.close()

def add_favorite(uid, symbol):
    try:
        conn = get_conn()
        conn.execute("INSERT INTO favorites (user_id,symbol) VALUES (?,?)", (uid, symbol.upper()))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def remove_favorite(uid, symbol):
    conn = get_conn()
    cur = conn.execute("DELETE FROM favorites WHERE user_id=? AND symbol=?", (uid, symbol.upper()))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_favorites(uid):
    conn = get_conn()
    rows = conn.execute("SELECT symbol FROM favorites WHERE user_id=? ORDER BY added_at DESC", (uid,)).fetchall()
    conn.close()
    return [r["symbol"] for r in rows]

# ====================== مصادر البيانات الحقيقية ======================
async def get_coin_data(symbol: str) -> dict:
    """جلب بيانات من CoinGecko (مجاني)"""
    symbol = symbol.lower().strip()
    result = {"source": "CoinGecko", "found": False}

    try:
        async with aiohttp.ClientSession() as session:
            # البحث عن الـ ID
            async with session.get(f"https://api.coingecko.com/api/v3/search?query={symbol}") as resp:
                search = await resp.json()
                coins = search.get("coins", [])
                if not coins:
                    return result
                coin_id = coins[0]["id"]
                name = coins[0]["name"]
                symbol_real = coins[0]["symbol"].upper()

            # جلب التفاصيل
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&community_data=false&developer_data=false"
            async with session.get(url) as resp:
                data = await resp.json()

            market = data.get("market_data", {})
            result.update({
                "found": True,
                "name": name,
                "symbol": symbol_real,
                "rank": market.get("market_cap_rank"),
                "price": market.get("current_price", {}).get("usd"),
                "market_cap": market.get("market_cap", {}).get("usd"),
                "volume_24h": market.get("total_volume", {}).get("usd"),
                "circulating": market.get("circulating_supply"),
                "total_supply": market.get("total_supply"),
                "max_supply": market.get("max_supply"),
                "ath": market.get("ath", {}).get("usd"),
                "ath_change": market.get("ath_change_percentage", {}).get("usd"),
                "change_24h": market.get("price_change_percentage_24h"),
                "high_24h": market.get("high_24h", {}).get("usd"),
                "low_24h": market.get("low_24h", {}).get("usd"),
            })
    except Exception as e:
        result["error"] = str(e)
    return result

def format_number(n):
    if n is None: return "غير متوفر"
    if n >= 1_000_000_000: return f"{n/1_000_000_000:.2f}B"
    if n >= 1_000_000: return f"{n/1_000_000:.2f}M"
    if n >= 1_000: return f"{n/1_000:.2f}K"
    return f"{n:,.2f}"

# ====================== الأوامر ======================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 الاشتراكات VIP", callback_data="plans")],
        [InlineKeyboardButton(text="📈 Spot", callback_data="spot"), InlineKeyboardButton(text="🚀 Futures", callback_data="futures")],
        [InlineKeyboardButton(text="⭐ المفضلة", callback_data="favorites")],
        [InlineKeyboardButton(text="📊 تحليل أساسي", callback_data="fundamental")],
        [InlineKeyboardButton(text="📋 حالة اشتراكي", callback_data="status")],
        [InlineKeyboardButton(text="ℹ️ مساعدة", callback_data="help")]
    ])
    await message.answer(f"مرحباً <b>{message.from_user.first_name}</b>\n\n<b>Doshka Trading Pro</b>\nإشارات + تحليل أساسي حقيقي + On-chain", reply_markup=kb)

@dp.callback_query(F.data == "fundamental")
async def fundamental_menu(callback: types.CallbackQuery):
    if not is_subscribed(callback.from_user.id):
        await callback.answer("❌ هذا القسم للمشتركين فقط", show_alert=True)
        return
    await callback.message.edit_text(
        "<b>📊 التحليل الأساسي</b>\n\n"
        "أرسل رمز العملة مباشرة مثل:\n"
        "<code>BTC</code> أو <code>ETH</code> أو <code>SOL</code>\n\n"
        "سأجلب البيانات من CoinGecko:\n"
        "• الترتيب العالمي\n• السعر والقيمة السوقية\n• العرض المتداول والكلي\n• التغير 24 ساعة",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="back_main")]])
    )
    await callback.answer()

@dp.message(F.text.regexp(r"^[A-Za-z0-9]{1,15}$"))
async def analyze_coin(message: types.Message):
    if not is_subscribed(message.from_user.id):
        return
    symbol = message.text.strip().upper()
    wait = await message.reply(f"⏳ جاري تحليل <b>{symbol}</b>...")

    data = await get_coin_data(symbol)
    if not data.get("found"):
        await wait.edit_text(f"❌ لم أجد بيانات لـ {symbol}")
        return

    text = (
        f"<b>📊 تحليل {data['name']} ({data['symbol']})</b>\n"
        f"المصدر: CoinGecko\n\n"
        f"🏆 الترتيب العالمي: <b>#{data['rank'] or 'N/A'}</b>\n"
        f"💵 السعر: <b>${data['price']:,.4f}</b>\n"
        f"📈 القيمة السوقية: <b>${format_number(data['market_cap'])}</b>\n"
        f"🔄 حجم 24 ساعة: <b>${format_number(data['volume_24h'])}</b>\n\n"
        f"📦 العرض المتداول: <b>{format_number(data['circulating'])}</b>\n"
        f"📦 إجمالي العرض: <b>{format_number(data['total_supply'])}</b>\n"
        f"📦 أقصى عرض: <b>{format_number(data['max_supply'])}</b>\n\n"
        f"📉 من ATH: <b>{data['ath_change']:.1f}%</b>\n"
        f"📊 التغير 24س: <b>{data['change_24h']:.2f}%</b>"
    )
    await wait.edit_text(text)

# ===== باقي الأوامر الأساسية =====
@dp.callback_query(F.data == "favorites")
async def favorites_menu(callback: types.CallbackQuery):
    favs = get_favorites(callback.from_user.id)
    text = "<b>⭐ عملاتك المفضلة</b>\n\n" + ("\n".join(f"• {s}" for s in favs) if favs else "لا توجد")
    text += "\n\n<code>/add BTC</code> | <code>/remove BTC</code>"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙", callback_data="back_main")]]))
    await callback.answer()

@dp.message(Command("add"))
async def add_cmd(message: types.Message, command: CommandObject):
    if not command.args:
        await message.reply("مثال: /add BTC")
        return
    if add_favorite(message.from_user.id, command.args):
        await message.reply(f"✅ تمت إضافة {command.args.upper()}")
    else:
        await message.reply("موجودة مسبقاً")

@dp.message(Command("remove"))
async def remove_cmd(message: types.Message, command: CommandObject):
    if not command.args:
        await message.reply("مثال: /remove BTC")
        return
    if remove_favorite(message.from_user.id, command.args):
        await message.reply("✅ تم الحذف")
    else:
        await message.reply("غير موجودة")

@dp.callback_query(F.data == "plans")
async def plans_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="شهر — 20$", callback_data="buy_1m")],
        [InlineKeyboardButton(text="3 أشهر — 50$", callback_data="buy_3m")],
        [InlineKeyboardButton(text="6 أشهر — 75$", callback_data="buy_6m")],
        [InlineKeyboardButton(text="سنة — 125$", callback_data="buy_1y")],
        [InlineKeyboardButton(text="🔙", callback_data="back_main")]
    ])
    await callback.message.edit_text("<b>💎 باقات VIP</b>", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy_plan(callback: types.CallbackQuery):
    plan = callback.data.split("_")[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Solana", callback_data=f"pay_{plan}_sol")],
        [InlineKeyboardButton(text="BNB", callback_data=f"pay_{plan}_bnb")],
        [InlineKeyboardButton(text="ETH", callback_data=f"pay_{plan}_eth")]
    ])
    await callback.message.edit_text(f"<b>{PLANS[plan]['name']}</b> — {PLANS[plan]['price']}$", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_"))
async def pay_info(callback: types.CallbackQuery):
    _, plan, network = callback.data.split("_")
    wallet = SOL_WALLET if network == "sol" else BNB_ETH_WALLET
    await callback.message.edit_text(
        f"الباقة: {PLANS[plan]['name']}\nالمبلغ: {PLANS[plan]['price']}$\n\n"
        f"<code>{wallet}</code>\n\n"
        f"/verify {plan} {network} TX_HASH"
    )
    await callback.answer()

@dp.message(Command("verify"))
async def verify_cmd(message: types.Message, command: CommandObject):
    try:
        plan, network, tx = command.args.split()
        if is_hash_used(tx):
            await message.reply("الهاش مستخدم مسبقاً")
            return
        expire = activate_sub(message.from_user.id, plan, message.from_user.username, message.from_user.full_name)
        mark_hash(tx, message.from_user.id, plan, network)
        await message.reply(f"✅ تم التفعيل\nينتهي: {expire}")
        await bot.send_message(ADMIN_ID, f"اشتراك جديد\n{message.from_user.id}\n{plan}\n{tx}")
    except:
        await message.reply("الصيغة: /verify 1m sol TXHASH")

@dp.callback_query(F.data == "status")
async def status_cmd(callback: types.CallbackQuery):
    text = "✅ اشتراكك نشط" if is_subscribed(callback.from_user.id) else "❌ لا يوجد اشتراك"
    await callback.message.edit_text(text)
    await callback.answer()

@dp.callback_query(F.data == "back_main")
async def back(callback: types.CallbackQuery):
    await cmd_start(callback.message)
    await callback.answer()

@dp.message(Command("admin"))
async def admin_cmd(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer("لوحة الأدمن\n/give USER_ID 1m")

@dp.message(Command("give"))
async def give_cmd(message: types.Message, command: CommandObject):
    if not is_admin(message.from_user.id): return
    try:
        uid, plan = command.args.split()
        expire = activate_sub(int(uid), plan)
        await message.reply(f"تم إعطاء {plan} لـ {uid}\nينتهي {expire}")
    except:
        await message.reply("/give 123456 1m")

async def main():
    init_db()
    print("البوت يعمل الآن مع CoinGecko...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
