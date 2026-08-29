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
async def cmd
