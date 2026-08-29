"""
Doshka Trading Pro — نسخة Railway
تقرأ الإعدادات من متغيرات البيئة
"""

import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import time
import io

import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, Message, BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# ====================== الإعدادات من Railway ======================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# محافظ Trust Wallet
SOL_WALLET = os.getenv("SOL_WALLET", "")
ETH_WALLET = os.getenv("ETH_WALLET", "").lower()
BNB_WALLET = os.getenv("BNB_WALLET", "").lower()

# قاعدة البيانات - Railway يوفر PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "")
SQLITE_PATH = os.getenv("SQLITE_PATH", "/data/subscriptions.db")

PAYMENT_TOLERANCE = 0.15

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN غير موجود! تأكد من إضافته في Railway Variables")
    raise SystemExit("❌ BOT_TOKEN مطلوب")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("doshka")

# ====================== الخطط ======================
PLANS = {
    "1m": {"days": 30, "price": 20, "name": "شهر", "emoji": "📅"},
    "3m": {"days": 90, "price": 50, "name": "3 أشهر", "emoji": "💎"},
    "6m": {"days": 180, "price": 75, "name": "6 أشهر", "emoji": "👑"},
    "1y": {"days": 365, "price": 125, "name": "سنة", "emoji": "🏆"},
}

# ====================== المدارس ======================
TRADING_SCHOOLS = {
    "wyckoff": {"name": "وايكوف", "emoji": "📊", "timeframes": ["1h", "4h", "1d"]},
    "elliott": {"name": "إليوت", "emoji": "🌊", "timeframes": ["1h", "4h"]},
    "classic": {"name": "كلاسيكي", "emoji": "📈", "timeframes": ["15m", "1h", "4h"]},
}

# ====================== FSM ======================
class AnalysisStates(StatesGroup):
    waiting_for_custom_symbol = State()
    waiting_for_tx_hash = State()

# ====================== البوت ======================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ====================== قاعدة البيانات ======================
class Database:
    def __init__(self):
        self.use_postgres = bool(DATABASE_URL)
        self.pool = None
        self.sqlite_path = SQLITE_PATH
    
    async def init(self):
        if self.use_postgres:
            await self._init_postgres()
        else:
            await self._init_sqlite()
    
    async def _init_postgres(self):
        try:
            import asyncpg
            self.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        plan TEXT,
                        start_date TIMESTAMPTZ,
                        expire_date TIMESTAMPTZ,
                        is_active BOOLEAN DEFAULT FALSE
                    );
                    CREATE TABLE IF NOT EXISTS used_hashes (
                        tx_hash TEXT PRIMARY KEY,
                        user_id BIGINT,
                        plan TEXT,
                        network TEXT,
                        amount_usd NUMERIC
                    );
                """)
                await conn.execute(
                    "INSERT INTO users (user_id, is_active) VALUES ($1, TRUE) ON CONFLICT DO NOTHING",
                    ADMIN_ID
                )
            logger.info("✅ PostgreSQL ready")
        except Exception as e:
            logger.error(f"PostgreSQL error: {e}")
            await self._init_sqlite()
    
    async def _init_sqlite(self):
        import sqlite3
        os.makedirs(os.path.dirname(self.sqlite_path) or ".", exist_ok=True)
        conn = sqlite3.connect(self.sqlite_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                plan TEXT,
                start_date TEXT,
                expire_date TEXT,
                is_active INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS used_hashes (
                tx_hash TEXT PRIMARY KEY,
                user_id INTEGER,
                plan TEXT,
                network TEXT,
                amount_usd REAL
            );
        """)
        conn.execute("INSERT OR IGNORE INTO users (user_id, is_active) VALUES (?, 1)", (ADMIN_ID,))
        conn.commit()
        conn.close()
        logger.info("✅ SQLite ready")
    
    async def is_subscribed(self, uid: int) -> bool:
        if uid == ADMIN_ID:
            return True
        
        if self.use_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT expire_date FROM users WHERE user_id=$1 AND is_active=TRUE",
                    uid
                )
                if not row or not row["expire_date"]:
                    return False
                return row["expire_date"] > datetime.utcnow()
        else:
            import sqlite3
            conn = sqlite3.connect(self.sqlite_path)
            row = conn.execute(
                "SELECT expire_date FROM users WHERE user_id=? AND is_active=1",
                (uid,)
            ).fetchone()
            conn.close()
            if not row or not row[0]:
                return False
            return datetime.fromisoformat(row[0]) > datetime.now()
    
    async def activate_subscription(self, uid: int, plan: str) -> str:
        expire = datetime.utcnow() + timedelta(days=PLANS[plan]["days"])
        
        if self.use_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (user_id, plan, start_date, expire_date, is_active)
                    VALUES ($1, $2, NOW(), $3, TRUE)
                    ON CONFLICT (user_id) DO UPDATE SET
                        plan = EXCLUDED.plan,
                        start_date = NOW(),
                        expire_date = EXCLUDED.expire_date,
                        is_active = TRUE
                """, uid, plan, expire)
        else:
            import sqlite3
            conn = sqlite3.connect(self.sqlite_path)
            conn.execute("""
                INSERT INTO users (user_id, plan, start_date, expire_date, is_active)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    plan = excluded.plan,
                    start_date = excluded.start_date,
                    expire_date = excluded.expire_date,
                    is_active = 1
            """, (uid, plan, datetime.now().isoformat(), expire.isoformat()))
            conn.commit()
            conn.close()
        
        return expire.strftime("%Y-%m-%d %H:%M")
    
    async def is_hash_used(self, tx_hash: str) -> bool:
        tx_hash = tx_hash.lower().strip()
        
        if self.use_postgres and self.pool:
            async with self.pool.acquire() as conn:
                return bool(await conn.fetchval(
                    "SELECT 1 FROM used_hashes WHERE tx_hash=$1", tx_hash
                ))
        else:
            import sqlite3
            conn = sqlite3.connect(self.sqlite_path)
            result = conn.execute(
                "SELECT 1 FROM used_hashes WHERE tx_hash=?",
                (tx_hash,)
            ).fetchone()
            conn.close()
            return bool(result)
    
    async def mark_hash_used(self, tx_hash: str, uid: int, plan: str, network: str, amount: float):
        tx_hash = tx_hash.lower().strip()
        
        if self.use_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO used_hashes (tx_hash, user_id, plan, network, amount_usd) VALUES ($1, $2, $3, $4, $5)",
                    tx_hash, uid, plan, network, amount
                )
        else:
            import sqlite3
            conn = sqlite3.connect(self.sqlite_path)
            conn.execute(
                "INSERT INTO used_hashes (tx_hash, user_id, plan, network, amount_usd) VALUES (?, ?, ?, ?, ?)",
                (tx_hash, uid, plan, network, amount)
            )
            conn.commit()
            conn.close()

db = Database()

# ====================== جلب الأسعار ======================
async def get_price(coin_id: str) -> Optional[float]:
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return float(data[coin_id]["usd"])
        return None
    except:
        return None

# ====================== التحقق من المعاملات ======================
async def verify_eth_or_bnb_tx(tx_hash: str, expected_usd: float, network: str) -> tuple:
    try:
        tx_hash = tx_hash.lower().strip()
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash
        
        if network == "eth":
            rpc_url = "https://ethereum.publicnode.com"
            wallet = ETH_WALLET
            coin_id = "ethereum"
            coin_name = "ETH"
        else:
            rpc_url = "https://bsc.publicnode.com"
            wallet = BNB_WALLET
            coin_id = "binancecoin"
            coin_name = "BNB"
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getTransactionByHash",
                "params": [tx_hash]
            }
            
            async with session.post(rpc_url, json=payload, timeout=15) as resp:
                data = await resp.json()
            
            tx = data.get("result")
            if not tx:
                return False, "❌ المعاملة غير موجودة", 0
            
            to_address = (tx.get("to") or "").lower()
            
            if to_address != wallet:
                return False, "❌ المعاملة ليست لمحفظتك", 0
            
            value_wei = int(tx.get("value", "0x0"), 16)
            amount_native = value_wei / 1e18
            
            price = await get_price(coin_id)
            if not price:
                return False, "❌ تعذر جلب السعر", 0
            
            received_amount = amount_native * price
            
            receipt_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash]
            }
            
            async with session.post(rpc_url, json=receipt_payload, timeout=15) as resp:
                receipt_data = await resp.json()
            
            receipt = receipt_data.get("result")
            if receipt and receipt.get("status") != "0x1":
                return False, "❌ المعاملة فشلت", 0
            
            min_acceptable = expected_usd * (1 - PAYMENT_TOLERANCE)
            if received_amount < min_acceptable:
                return False, f"❌ المبلغ غير كافٍ (${received_amount:.2f})", received_amount
            
            return True, f"✅ تم استلام ${received_amount:.2f} {coin_name}", received_amount
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return False, f"❌ خطأ: {str(e)[:80]}", 0

async def verify_solana_tx(tx_hash: str, expected_usd: float) -> tuple:
    try:
        rpc_url = "https://api.mainnet-beta.solana.com"
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [tx_hash, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
            }
            
            async with session.post(rpc_url, json=payload, timeout=15) as resp:
                data = await resp.json()
            
            if "error" in data:
                return False, "❌ المعاملة غير موجودة", 0
            
            result = data.get("result")
            if not result:
                return False, "❌ لم يتم العثور على المعاملة", 0
            
            if result.get("meta", {}).get("err"):
                return False, "❌ المعاملة فشلت", 0
            
            pre_balances = result["meta"].get("preBalances", [])
            post_balances = result["meta"].get("postBalances", [])
            account_keys = result["transaction"]["message"].get("accountKeys", [])
            
            received_amount = 0
            
            for i, key in enumerate(account_keys):
                pubkey = key.get("pubkey") if isinstance(key, dict) else key
                
                if pubkey == SOL_WALLET and i < len(pre_balances) and i < len(post_balances):
                    amount_sol = (post_balances[i] - pre_balances[i]) / 1e9
                    if amount_sol > 0:
                        sol_price = await get_price("solana")
                        if sol_price:
                            received_amount = amount_sol * sol_price
            
            if received_amount <= 0:
                return False, "❌ لا يوجد تحويل لمحفظتك", 0
            
            min_acceptable = expected_usd * (1 - PAYMENT_TOLERANCE)
            if received_amount < min_acceptable:
                return False, f"❌ المبلغ غير كافٍ (${received_amount:.2f})", received_amount
            
            return True, f"✅ تم استلام ${received_amount:.2f} SOL", received_amount
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return False, f"❌ خطأ: {str(e)[:80]}", 0

# ====================== جلب البيانات ======================
async def get_klines(symbol: str, interval: str = "4h", limit: int = 100) -> List[Dict]:
    try:
        symbol = symbol.upper().replace("USDT", "")
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval={interval}&limit={limit}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
        
        return [{
            "open": float(k[1]), "high": float(k[2]),
            "low": float(k[3]), "close": float(k[4]),
            "volume": float(k[5]),
            "time": datetime.fromtimestamp(k[0]/1000)
        } for k in data]
    except:
        return []

# ====================== المؤشرات ======================
def calculate_rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        gains.append(max(0, change))
        losses.append(max(0, -change))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    return 100 - (100 / (1 + avg_gain / avg_loss))

def find_sr(klines: List[Dict]) -> Dict:
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    levels = []
    for i in range(2, len(highs) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            levels.append(highs[i])
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            levels.append(lows[i])
    current = klines[-1]["close"]
    supports = sorted([l for l in levels if l < current], reverse=True)[:3]
    resistances = sorted([l for l in levels if l > current])[:3]
    return {"supports": supports, "resistances": resistances}

# ====================== التحليل ======================
def analyze(klines: List[Dict], symbol: str, school: str) -> Dict:
    if len(klines) < 30:
        return None
    
    closes = [k["close"] for k in klines]
    current = closes[-1]
    rsi = calculate_rsi(closes)
    sr = find_sr(klines)
    
    action = "WAIT"
    confidence = 50
    
    if rsi < 30:
        action = "BUY"
        confidence = 80
    elif rsi > 70:
        action = "SELL"
        confidence = 80
    
    if action == "BUY":
        entry = [round(current, 4)]
        if sr["supports"]:
            entry.append(round(sr["supports"][0], 4))
        stop_loss = round(min(k["low"] for k in klines[-20:]) * 0.97, 4)
        take_profit = [round(current * 1.03, 4), round(current * 1.06, 4)]
    elif action == "SELL":
        entry = [round(current, 4)]
        if sr["resistances"]:
            entry.append(round(sr["resistances"][0], 4))
        stop_loss = round(max(k["high"] for k in klines[-20:]) * 1.03, 4)
        take_profit = [round(current * 0.97, 4), round(current * 0.94, 4)]
    else:
        entry = [round(current, 4)]
        stop_loss = round(current * 0.95, 4)
        take_profit = [round(current * 1.05, 4)]
    
    action_text = {"BUY": "📈 شراء", "SELL": "📉 بيع", "WAIT": "⏳ انتظار"}[action]
    
    analysis_text = (
        f"📊 <b>تحليل {symbol}/USDT</b>\n"
        f"المدرسة: {TRADING_SCHOOLS[school]['name']}\n\n"
        f"RSI: <b>{rsi:.1f}</b>\n"
        f"التوصية: <b>{action_text}</b>\n"
        f"الثقة: <b>{confidence}%</b>\n\n"
        f"💡 الدخول: {', '.join([f'${e}' for e in entry])}\n"
        f"🛑 الوقف: ${stop_loss}\n"
        f"🎯 الأهداف: {', '.join([f'${tp}' for tp in take_profit])}"
    )
    
    return {
        "analysis": analysis_text,
        "action": action,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "sr": sr
    }

# ====================== الرسم ======================
def create_chart(klines: List[Dict], symbol: str, signal: Dict) -> io.BytesIO:
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor('#0d1117')
    
    dates = [k["time"] for k in klines]
    opens = [k["open"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    closes = [k["close"] for k in klines]
    
    for i in range(len(klines)):
        color = '#26a69a' if closes[i] >= opens[i] else '#ef5350'
        ax.plot([dates[i], dates[i]], [opens[i], closes[i]], color=color, linewidth=3)
        ax.plot([dates[i], dates[i]], [lows[i], highs[i]], color=color, linewidth=1)
    
    for support in signal["sr"]["supports"]:
        ax.axhline(y=support, color='#4caf50', linestyle='--', alpha=0.7)
    for resistance in signal["sr"]["resistances"]:
        ax.axhline(y=resistance, color='#f44336', linestyle='--', alpha=0.7)
    
    for entry in signal["entry"]:
        ax.axhline(y=entry, color='#ffd700', linestyle='-', alpha=0.8)
    ax.axhline(y=signal["stop_loss"], color='#ff1744', linestyle='-', alpha=0.9)
    for tp in signal["take_profit"]:
        ax.axhline(y=tp, color='#00e676', linestyle='-', alpha=0.8)
    
    ax.set_title(f'{symbol}/USDT', fontsize=16, fontweight='bold', color='white')
    ax.grid(True, alpha=0.3)
    ax.tick_params(colors='white')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, facecolor='#0d1117')
    buf.seek(0)
    plt.close()
    return buf

# ====================== لوحات ======================
def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_main")]
    ])

def main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 التحليل الفني", callback_data="start_analysis"))
    builder.row(InlineKeyboardButton(text="💎 الاشتراكات", callback_data="plans"))
    builder.row(
        InlineKeyboardButton(text="ℹ️ مساعدة", callback_data="help"),
        InlineKeyboardButton(text="📋 حالتي", callback_data="status")
    )
    return builder.as_markup()

def schools_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sid, school in TRADING_SCHOOLS.items():
        builder.row(InlineKeyboardButton(
            text=f"{school['emoji']} {school['name']}",
            callback_data=f"school_{sid}"
        ))
    builder.row(InlineKeyboardButton(text="🔙", callback_data="back_main"))
    return builder.as_markup()

def timeframes_kb(sid: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for tf in TRADING_SCHOOLS[sid]["timeframes"]:
        builder.row(InlineKeyboardButton(text=f"⏰ {tf}", callback_data=f"tf_{sid}_{tf}"))
    builder.row(InlineKeyboardButton(text="🔙", callback_data="start_analysis"))
    return builder.as_markup()

def coins_kb(sid: str, tf: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    coins = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX"]
    for i in range(0, len(coins), 2):
        row = [InlineKeyboardButton(text=f"💰 {c}", callback_data=f"analyze_{sid}_{tf}_{c}") for c in coins[i:i+2]]
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="🔍 بحث", callback_data=f"custom_{sid}_{tf}"))
    builder.row(InlineKeyboardButton(text="🔙", callback_data=f"school_{sid}"))
    return builder.as_markup()

# ====================== المعالجات ======================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🌟 <b>Doshka Trading Pro</b>\n\n"
        "📊 تحليل فني احترافي\n"
        "💎 اشتراكات مدفوعة\n\n"
        "اختر من القائمة:",
        reply_markup=main_kb()
    )

@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    await callback.message.edit_text("🌟 <b>Doshka Trading Pro</b>", reply_markup=main_kb())
    await callback.answer()

@dp.callback_query(F.data == "start_analysis")
async def start_analysis(callback: CallbackQuery):
    if not await db.is_subscribed(callback.from_user.id):
        await callback.answer("❌ للمشتركين فقط", show_alert=True)
        return
    await callback.message.edit_text("📊 <b>اختر المدرسة:</b>", reply_markup=schools_kb())
    await callback.answer()

@dp.callback_query(F.data.startswith("school_"))
async def choose_school(callback: CallbackQuery):
    sid = callback.data.split("_")[1]
    await callback.message.edit_text(
        f"{TRADING_SCHOOLS[sid]['emoji']} <b>{TRADING_SCHOOLS[sid]['name']}</b>",
        reply_markup=timeframes_kb(sid)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("tf_"))
async def choose_tf(callback: CallbackQuery):
    _, sid, tf = callback.data.split("_")
    await callback.message.edit_text("💰 <b>اختر العملة:</b>", reply_markup=coins_kb(sid, tf))
    await callback.answer()

@dp.callback_query(F.data.startswith("custom_"))
async def custom(callback: CallbackQuery, state: FSMContext):
    _, sid, tf = callback.data.split("_")
    await state.update_data(sid=sid, tf=tf)
    await state.set_state(AnalysisStates.waiting_for_custom_symbol)
    await callback.message.edit_text("🔍 <b>أدخل رمز العملة:</b>")
    await callback.answer()

@dp.message(StateFilter(AnalysisStates.waiting_for_custom_symbol))
async def process_custom(message: Message, state: FSMContext):
    data = await state.get_data()
    sid = data["sid"]
    tf = data["tf"]
    symbol = message.text.strip().upper()
    await state.clear()
    await do_analysis(message, symbol, sid, tf)

@dp.callback_query(F.data.startswith("analyze_"))
async def analyze_cb(callback: CallbackQuery):
    _, sid, tf, symbol = callback.data.split("_")
    await callback.answer("⏳ جاري التحليل...")
    await do_analysis(callback.message, symbol, sid, tf)

async def do_analysis(message: Message, symbol: str, sid: str, tf: str):
    wait = await message.answer(f"⏳ جاري تحليل {symbol}...")
    
    klines = await get_klines(symbol, tf, 100)
    if not klines:
        await wait.edit_text(f"❌ تعذر جلب بيانات {symbol}")
        return
    
    signal = analyze(klines, symbol, sid)
    if not signal:
        await wait.edit_text("❌ بيانات غير كافية")
        return
    
    chart = create_chart(klines, symbol, signal)
    
    await wait.delete()
    await message.answer_photo(
        photo=BufferedInputFile(chart.read(), filename=f"{symbol}.png"),
        caption=signal["analysis"],
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 تحليل آخر", callback_data="start_analysis")],
            [InlineKeyboardButton(text="🔙", callback_data="back_main")]
        ])
    )

# ====================== نظام الدفع ======================
@dp.callback_query(F.data == "plans")
async def show_plans(callback: CallbackQuery):
    text = "<b>💎 خطط الاشتراك:</b>\n\n"
    builder = InlineKeyboardBuilder()
    
    for plan_id, plan in PLANS.items():
        text += f"{plan['emoji']} {plan['name']}: ${plan['price']}\n"
        builder.row(InlineKeyboardButton(
            text=f"{plan['emoji']} {plan['name']} - ${plan['price']}",
            callback_data=f"subscribe_{plan_id}"
        ))
    
    builder.row(InlineKeyboardButton(text="🔙", callback_data="back_main"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("subscribe_"))
async def subscribe_plan(callback: CallbackQuery):
    plan_id = callback.data.split("_")[1]
    plan = PLANS[plan_id]
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◎ Solana", callback_data=f"net_{plan_id}_sol"))
    builder.row(InlineKeyboardButton(text="Ξ Ethereum", callback_data=f"net_{plan_id}_eth"))
    builder.row(InlineKeyboardButton(text="🟡 BNB Chain", callback_data=f"net_{plan_id}_bnb"))
    builder.row(InlineKeyboardButton(text="🔙", callback_data="plans"))
    
    await callback.message.edit_text(
        f"💳 <b>الدفع - {plan['name']}</b>\n"
        f"💰 المبلغ: ${plan['price']}\n\n"
        f"اختر الشبكة:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("net_"))
async def choose_network(callback: CallbackQuery, state: FSMContext):
    _, plan_id, network = callback.data.split("_")
    plan = PLANS[plan_id]
    
    wallets = {"sol": SOL_WALLET, "eth": ETH_WALLET, "bnb": BNB_WALLET}
    names = {"sol": "Solana", "eth": "Ethereum", "bnb": "BNB Chain"}
    
    await state.update_data(plan_id=plan_id, network=network)
    await state.set_state(AnalysisStates.waiting_for_tx_hash)
    
    await callback.message.edit_text(
        f"💳 <b>الدفع - {plan['name']}</b>\n"
        f"الشبكة: <b>{names[network]}</b>\n"
        f"المبلغ: <b>${plan['price']}</b>\n\n"
        f"📮 <b>أرسل إلى:</b>\n"
        f"<code>{wallets[network]}</code>\n\n"
        f"بعد الدفع أرسل Transaction Hash:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 إلغاء", callback_data="plans")]
        ])
    )
    await callback.answer()

@dp.message(StateFilter(AnalysisStates.waiting_for_tx_hash))
async def process_tx(message: Message, state: FSMContext):
    tx_hash = message.text.strip()
    data = await state.get_data()
    plan_id = data.get("plan_id")
    network = data.get("network")
    
    if await db.is_hash_used(tx_hash):
        await state.clear()
        await message.reply("❌ هذا الهاش مستخدم مسبقاً")
        return
    
    wait = await message.reply("⏳ جاري التحقق من المعاملة...")
    
    expected = PLANS[plan_id]["price"]
    
    if network == "sol":
        success, msg, amount = await verify_solana_tx(tx_hash, expected)
    else:
        success, msg, amount = await verify_eth_or_bnb_tx(tx_hash, expected, network)
    
    if not success:
        await wait.edit_text(f"❌ <b>فشل التحقق</b>\n\n{msg}")
        await state.clear()
        return
    
    expire = await db.activate_subscription(message.from_user.id, plan_id)
    await db.mark_hash_used(tx_hash, message.from_user.id, plan_id, network, amount)
    
    await wait.edit_text(
        f"🎉 <b>تم التفعيل!</b>\n\n"
        f"{msg}\n"
        f"📦 الباقة: {PLANS[plan_id]['name']}\n"
        f"📅 ينتهي: {expire}"
    )
    
    await state.clear()

@dp.callback_query(F.data == "status")
async def check_status(callback: CallbackQuery):
    is_active = await db.is_subscribed(callback.from_user.id)
    text = "✅ <b>اشتراكك نشط</b>" if is_active else "❌ <b>لا يوجد اشتراك</b>"
    await callback.message.edit_text(text, reply_markup=back_kb())
    await callback.answer()

@dp.callback_query(F.data == "help")
async def help_cb(callback: CallbackQuery):
    text = (
        "<b>📖 المساعدة:</b>\n\n"
        "1. التحليل الفني\n"
        "2. اختر المدرسة\n"
        "3. اختر العملة\n\n"
        "<b>الدفع:</b>\n"
        "Solana, Ethereum, BNB"
    )
    await callback.message.edit_text(text, reply_markup=back_kb())
    await callback.answer()

# ====================== التشغيل ======================
async def main():
    await db.init()
    logger.info(f"✅ BOT_TOKEN: {BOT_TOKEN[:10]}...")
    logger.info(f"✅ ADMIN_ID: {ADMIN_ID}")
    logger.info(f"✅ SOL_WALLET: {SOL_WALLET[:10]}..." if SOL_WALLET else "⚠️ SOL_WALLET غير مضاف")
    logger.info(f"✅ ETH_WALLET: {ETH_WALLET[:10]}..." if ETH_WALLET else "⚠️ ETH_WALLET غير مضاف")
    logger.info(f"✅ BNB_WALLET: {BNB_WALLET[:10]}..." if BNB_WALLET else "⚠️ BNB_WALLET غير مضاف")
    logger.info("🚀 البوت يعمل...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
