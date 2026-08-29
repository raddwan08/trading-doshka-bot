ADMIN_ID
SQLITE_PATH

SOL_WALLET
ETH_WALLET
BNB_WALLET

ETH_RPC_URL       (optional, default public RPC)
BNB_RPC_URL       (optional, default public RPC)
SOL_RPC_URL       (optional, default Solana mainnet RPC)

PAYMENT_SCAN_SECONDS=15
PAYMENT_TOLERANCE_USDT=0.01
PAYMENT_MAX_AGE_HOURS=24
"""

import asyncio
import io
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

SQLITE_PATH = os.getenv("SQLITE_PATH", "data/subscriptions.db")

SOL_WALLET = os.getenv("SOL_WALLET", "").strip()
ETH_WALLET = os.getenv("ETH_WALLET", "").strip().lower()
BNB_WALLET = os.getenv("BNB_WALLET", "").strip().lower()

ETH_RPC_URL = os.getenv("ETH_RPC_URL", "https://ethereum.publicnode.com").strip()
BNB_RPC_URL = os.getenv("BNB_RPC_URL", "https://bsc.publicnode.com").strip()
SOL_RPC_URL = os.getenv(
    "SOL_RPC_URL", "https://api.mainnet-beta.solana.com"
).strip()

PAYMENT_SCAN_SECONDS = max(5, int(os.getenv("PAYMENT_SCAN_SECONDS", "15")))
PAYMENT_TOLERANCE_USDT = max(0.0, float(os.getenv("PAYMENT_TOLERANCE_USDT", "0.01")))
PAYMENT_MAX_AGE_HOURS = max(1, int(os.getenv("PAYMENT_MAX_AGE_HOURS", "24")))

if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN مطلوب")

if not ADMIN_ID:
    raise SystemExit("ADMIN_ID مطلوب")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("doshka")


# =========================================================
# PLANS
# =========================================================

PLANS = {
    "1m": {"days": 30, "price": 20.0, "name": "شهر", "emoji": "📅"},
    "3m": {"days": 90, "price": 50.0, "name": "3 أشهر", "emoji": "💎"},
    "6m": {"days": 180, "price": 75.0, "name": "6 أشهر", "emoji": "👑"},
    "1y": {"days": 365, "price": 125.0, "name": "سنة", "emoji": "🏆"},
}


# =========================================================
# SCHOOLS
# =========================================================

TRADING_SCHOOLS = {
    "wyckoff": {
        "name": "وايكوف",
        "emoji": "📊",
        "timeframes": ["1h", "4h", "1d"],
        "color": "#FF6B6B",
    },
    "elliott": {
        "name": "إليوت",
        "emoji": "🌊",
        "timeframes": ["1h", "4h", "1d"],
        "color": "#4ECDC4",
    },
    "harmonic": {
        "name": "هارمونيك",
        "emoji": "🦋",
        "timeframes": ["1h", "4h", "1d"],
        "color": "#95E1D3",
    },
    "classic": {
        "name": "كلاسيكي",
        "emoji": "📈",
        "timeframes": ["15m", "1h", "4h", "1d"],
        "color": "#F38181",
    },
    "whales": {
        "name": "الحيتان",
        "emoji": "🐋",
        "timeframes": ["1h", "4h", "1d"],
        "color": "#AA96DA",
    },
    "tvl": {
        "name": "TVL",
        "emoji": "🔒",
        "timeframes": ["1d"],
        "color": "#FCE38A",
    },
}


# =========================================================
# FSM
# =========================================================

class AnalysisStates(StatesGroup):
    waiting_for_custom_symbol = State()


# =========================================================
# BOT
# =========================================================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


# =========================================================
# HELPERS
# =========================================================

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def format_dt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


# =========================================================
# DATABASE
# =========================================================

class Database:
    def __init__(self):
        self.sqlite_path = SQLITE_PATH
        self.lock = asyncio.Lock()

    def _connect(self):
        conn = sqlite3.connect(self.sqlite_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    async def init(self):
        os.makedirs(os.path.dirname(self.sqlite_path) or ".", exist_ok=True)

        async with self.lock:
            conn = self._connect()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        full_name TEXT,
                        plan TEXT,
                        start_date TEXT,
                        expire_date TEXT,
                        is_active INTEGER DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS payment_intents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        plan TEXT NOT NULL,
                        network TEXT NOT NULL,
                        wallet TEXT NOT NULL,
                        expected_usd REAL NOT NULL,
                        expected_native REAL NOT NULL,
                        native_price REAL NOT NULL,
                        created_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        tx_hash TEXT UNIQUE,
                        detected_amount_native REAL,
                        detected_amount_usd REAL,
                        detected_at TEXT,
                        error TEXT
                    );

                    CREATE INDEX IF NOT EXISTS idx_payment_intents_status
                    ON payment_intents(status);

                    CREATE INDEX IF NOT EXISTS idx_payment_intents_user
                    ON payment_intents(user_id);

                    CREATE TABLE IF NOT EXISTS used_transactions (
                        tx_hash TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        plan TEXT NOT NULL,
                        network TEXT NOT NULL,
                        amount_native REAL NOT NULL,
                        amount_usd REAL NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )

                conn.execute(
                    """
                    INSERT OR IGNORE INTO users
                    (user_id, username, full_name, is_active)
                    VALUES (?, ?, ?, 1)
                    """,
                    (ADMIN_ID, "admin", "Admin"),
                )
                conn.commit()
            finally:
                conn.close()

        logger.info("Database ready")

    async def upsert_user(
        self,
        user_id: int,
        username: Optional[str],
        full_name: Optional[str],
    ):
        async with self.lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO users(user_id, username, full_name)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username=excluded.username,
                        full_name=excluded.full_name
                    """,
                    (user_id, username or "", full_name or ""),
                )
                conn.commit()
            finally:
                conn.close()

    async def is_subscribed(self, uid: int) -> bool:
        if uid == ADMIN_ID:
            return True

        async with self.lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    """
                    SELECT expire_date
                    FROM users
                    WHERE user_id=? AND is_active=1
                    """,
                    (uid,),
                ).fetchone()
            finally:
                conn.close()

        if not row or not row["expire_date"]:
            return False

        try:
            expire = datetime.fromisoformat(row["expire_date"])
            return expire > utcnow()
        except Exception:
            return False

    async def get_user_status(self, uid: int):
        async with self.lock:
            conn = self._connect()
            try:
                return conn.execute(
                    """
                    SELECT plan, start_date, expire_date, is_active
                    FROM users WHERE user_id=?
                    """,
                    (uid,),
                ).fetchone()
            finally:
                conn.close()

    async def activate_subscription(
        self,
        uid: int,
        plan: str,
        username: str = "",
        full_name: str = "",
    ) -> str:
        now = utcnow()

        async with self.lock:
            conn = self._connect()
            try:
                current = conn.execute(
                    """
                    SELECT expire_date, is_active
                    FROM users WHERE user_id=?
                    """,
                    (uid,),
                ).fetchone()

                start = now
                if current and current["expire_date"]:
                    try:
                        old_expire = datetime.fromisoformat(current["expire_date"])
                        if old_expire > now:
                            start = old_expire
                    except Exception:
                        pass

                expire = start + timedelta(days=PLANS[plan]["days"])

                conn.execute(
                    """
                    INSERT INTO users
                    (user_id, username, full_name, plan,
                     start_date, expire_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username=excluded.username,
                        full_name=excluded.full_name,
                        plan=excluded.plan,
                        start_date=excluded.start_date,
                        expire_date=excluded.expire_date,
                        is_active=1
                    """,
                    (
                        uid,
                        username or "",
                        full_name or "",
                        plan,
                        iso_utc(start),
                        iso_utc(expire),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        return format_dt(expire)

    async def create_payment_intent(
        self,
        uid: int,
        plan: str,
        network: str,
        wallet: str,
        expected_usd: float,
        expected_native: float,
        native_price: float = 1.0,
    ) -> int:
        created = utcnow()
        expires = created + timedelta(hours=PAYMENT_MAX_AGE_HOURS)

        async with self.lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    UPDATE payment_intents
                    SET status='expired'
                    WHERE user_id=? AND status='pending'
                    """,
                    (uid,),
                )

                cur = conn.execute(
                    """
                    INSERT INTO payment_intents
                    (user_id, plan, network, wallet, expected_usd,
                     expected_native, native_price, created_at, expires_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                    """,
                    (
                        uid,
                        plan,
                        network,
                        wallet,
                        expected_usd,
                        expected_native,
                        native_price,
                        iso_utc(created),
                        iso_utc(expires),
                    ),
                )
                intent_id = cur.lastrowid
                conn.commit()
                return int(intent_id)
            finally:
                conn.close()

    async def get_pending_intents(self) -> List[sqlite3.Row]:
        now = iso_utc(utcnow())

        async with self.lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    UPDATE payment_intents
                    SET status='expired'
                    WHERE status='pending' AND expires_at <= ?
                    """,
                    (now,),
                )
                conn.commit()

                rows = conn.execute(
                    """
                    SELECT *
                    FROM payment_intents
                    WHERE status='pending'
                    ORDER BY id ASC
                    """
                ).fetchall()
                return rows
            finally:
                conn.close()

    async def get_intent(self, intent_id: int):
        async with self.lock:
            conn = self._connect()
            try:
                return conn.execute(
                    "SELECT * FROM payment_intents WHERE id=?",
                    (intent_id,),
                ).fetchone()
            finally:
                conn.close()

    async def intent_has_tx(self, tx_hash: str) -> bool:
        async with self.lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    """
                    SELECT 1 FROM used_transactions
                    WHERE tx_hash=?
                    """,
                    (tx_hash.lower(),),
                ).fetchone()
                return bool(row)
            finally:
                conn.close()

    async def complete_payment(
        self,
        intent_id: int,
        tx_hash: str,
        amount_native: float,
        amount_usd: float,
    ) -> bool:
        tx_hash = tx_hash.lower()

        async with self.lock:
            conn = self._connect()
            try:
                # Atomic uniqueness check.
                if conn.execute(
                    "SELECT 1 FROM used_transactions WHERE tx_hash=?",
                    (tx_hash,),
                ).fetchone():
                    return False

                intent = conn.execute(
                    "SELECT * FROM payment_intents WHERE id=?",
                    (intent_id,),
                ).fetchone()

                if not intent or intent["status"] != "pending":
                    return False

                conn.execute(
                    """
                    INSERT INTO used_transactions
                    (tx_hash, user_id, plan, network,
                     amount_native, amount_usd, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tx_hash,
                        intent["user_id"],
                        intent["plan"],
                        intent["network"],
                        amount_native,
                        amount_usd,
                        iso_utc(utcnow()),
                    ),
                )

                conn.execute(
                    """
                    UPDATE payment_intents
                    SET status='paid',
                        tx_hash=?,
                        detected_amount_native=?,
                        detected_amount_usd=?,
                        detected_at=?
                    WHERE id=?
                    """,
                    (
                        tx_hash,
                        amount_native,
                        amount_usd,
                        iso_utc(utcnow()),
                        intent_id,
                    ),
                )

                conn.commit()
                return True
            except sqlite3.IntegrityError:
                conn.rollback()
                return False
            finally:
                conn.close()

    async def fail_intent(self, intent_id: int, error: str):
        async with self.lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    UPDATE payment_intents
                    SET status='failed', error=?
                    WHERE id=? AND status='pending'
                    """,
                    (error[:500], intent_id),
                )
                conn.commit()
            finally:
                conn.close()


db = Database()


# =========================================================
# MARKET DATA
# =========================================================

async def get_json(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 15,
):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            params=params,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            if resp.status != 200:
                return None
            return await resp.json()


async def get_klines(
    symbol: str,
    interval: str = "4h",
    limit: int = 150,
) -> List[Dict]:
    try:
        symbol = symbol.upper().replace("/", "").replace("USDT", "").strip()
        url = "https://api.binance.com/api/v3/klines"

        data = await get_json(
            url,
            params={
                "symbol": f"{symbol}USDT",
                "interval": interval,
                "limit": min(limit, 1000),
            },
        )

        if not data or not isinstance(data, list):
            return []

        return [
            {
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "time": datetime.fromtimestamp(
                    k[0] / 1000, tz=timezone.utc
                ),
            }
            for k in data
        ]
    except Exception as e:
        logger.error("Klines error: %s", e)
        return []


async def get_native_price(network: str) -> Optional[float]:
    coin_id = {
        "eth": "ethereum",
        "bnb": "binancecoin",
        "sol": "solana",
    }.get(network)

    if not coin_id:
        return None

    headers = {}
    if COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = COINGECKO_API_KEY

    try:
        data = await get_json(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd"},
            headers=headers,
            timeout=15,
        )
        price = safe_float((data or {}).get(coin_id, {}).get("usd"))
        return price if price > 0 else None
    except Exception as e:
        logger.error("Price error %s: %s", network, e)
        return None


# =========================================================
# TECHNICAL INDICATORS
# =========================================================

def calculate_rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0

    gains = []
    losses = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(0.0, change))
        losses.append(max(0.0, -change))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_ema(values: List[float], period: int) -> List[float]:
    if not values:
        return []

    ema = [values[0]]
    multiplier = 2 / (period + 1)

    for value in values[1:]:
        ema.append((value - ema[-1]) * multiplier + ema[-1])

    return ema


def calculate_macd(closes: List[float]) -> Dict[str, float]:
    if len(closes) < 35:
        return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}

    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)
    macd_line = [
        ema12[i] - ema26[i]
        for i in range(len(closes))
    ]
    signal_line = calculate_ema(macd_line, 9)

    return {
        "macd": macd_line[-1],
        "signal": signal_line[-1],
        "histogram": macd_line[-1] - signal_line[-1],
    }


def find_sr(klines: List[Dict]) -> Dict:
    if len(klines) < 10:
        current = klines[-1]["close"]
        return {"supports": [], "resistances": []}

    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]

    levels = []

    for i in range(2, len(klines) - 2):
        if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            levels.append(highs[i])

        if lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            levels.append(lows[i])

    current = klines[-1]["close"]

    supports = sorted(
        [x for x in levels if x < current],
        reverse=True,
    )[:3]

    resistances = sorted(
        [x for x in levels if x > current]
    )[:3]

    return {
        "supports": supports,
        "resistances": resistances,
    }


def action_text(action: str) -> str:
    return {
        "BUY": "🟢 شراء",
        "SELL": "🔴 بيع",
        "WAIT": "⏳ انتظار",
    }.get(action, "⏳ انتظار")


def trade_levels(
    klines: List[Dict],
    action: str,
    tp1: float,
    tp2: float,
) -> Tuple[List[float], float, List[float]]:
    current = klines[-1]["close"]
    sr = find_sr(klines)

    if action == "BUY":
        entry = [round(current, 6)]
        if sr["supports"]:
            entry.append(round(sr["supports"][0], 6))
        stop = min(k["low"] for k in klines[-20:]) * 0.97
        targets = [current * tp1, current * tp2]

    elif action == "SELL":
        entry = [round(current, 6)]
        if sr["resistances"]:
            entry.append(round(sr["resistances"][0], 6))
        stop = max(k["high"] for k in klines[-20:]) * 1.03
        targets = [current * (2 - tp1), current * (2 - tp2)]

    else:
        entry = [round(current, 6)]
        stop = current * 0.95
        targets = [current * 1.05]

    return (
        entry,
        round(stop, 6),
        [round(x, 6) for x in targets],
    )


# =========================================================
# SCHOOL 1 — WYCKOFF
# =========================================================

def wyckoff_analysis(klines, symbol):
    closes = [k["close"] for k in klines]
    volumes = [k["volume"] for k in klines]

    current = closes[-1]
    rsi = calculate_rsi(closes)

    baseline = sum(volumes[:-10]) / max(1, len(volumes[:-10]))
    recent = sum(volumes[-10:]) / 10
    volume_ratio = recent / baseline if baseline else 1

    range_high = max(k["high"] for k in klines[-30:])
    range_low = min(k["low"] for k in klines[-30:])
    position = (
        (current - range_low) / (range_high - range_low)
        if range_high > range_low else 0.5
    )

    if volume_ratio > 1.5 and position < 0.35:
        action = "BUY"
        confidence = 82
        phase = "Accumulation / Spring محتمل"
    elif volume_ratio > 1.5 and position > 0.70:
        action = "SELL"
        confidence = 82
        phase = "Distribution / Upthrust محتمل"
    elif position < 0.30 and rsi < 50:
        action = "BUY"
        confidence = 68
        phase = "Accumulation"
    elif position > 0.70 and rsi > 50:
        action = "SELL"
        confidence = 68
        phase = "Distribution"
    else:
        action = "WAIT"
        confidence = 52
        phase = "Trading Range"

    entry, stop, targets = trade_levels(
        klines, action, 1.03, 1.06
    )

    return {
        "analysis": (
            f"📊 <b>وايكوف — {symbol}/USDT</b>\n\n"
            f"المرحلة: <b>{phase}</b>\n"
            f"موقع السعر داخل النطاق: <b>{position*100:.1f}%</b>\n"
            f"Volume Ratio: <b>{volume_ratio:.2f}x</b>\n"
            f"RSI: <b>{rsi:.1f}</b>\n\n"
            f"التوصية: <b>{action_text(action)}</b>\n"
            f"الثقة: <b>{confidence}%</b>\n\n"
            f"💡 الدخول: {', '.join('$'+str(x) for x in entry)}\n"
            f"🛑 الوقف: ${stop}\n"
            f"🎯 الأهداف: {', '.join('$'+str(x) for x in targets)}"
        ),
        "action": action,
        "confidence": confidence,
        "entry": entry,
        "stop_loss": stop,
        "take_profit": targets,
        "sr": find_sr(klines),
        "school": "wyckoff",
        "extra": {"phase": phase, "volume_ratio": volume_ratio},
    }


# =========================================================
# SCHOOL 2 — ELLIOTT
# =========================================================

def _pivot_points(klines, depth=3):
    pivots = []

    for i in range(depth, len(klines) - depth):
        high = klines[i]["high"]
        low = klines[i]["low"]

        is_high = all(
            high > klines[j]["high"]
            for j in range(i - depth, i + depth + 1)
            if j != i
        )

        is_low = all(
            low < klines[j]["low"]
            for j in range(i - depth, i + depth + 1)
            if j != i
        )

        if is_high:
            pivots.append({"type": "H", "price": high, "index": i})
        elif is_low:
            pivots.append({"type": "L", "price": low, "index": i})

    return pivots


def elliott_analysis(klines, symbol):
    closes = [k["close"] for k in klines]
    current = closes[-1]
    pivots = _pivot_points(klines, 3)

    rsi = calculate_rsi(closes)

    action = "WAIT"
    confidence = 52
    wave = "عدّ موجي غير مكتمل"

    if len(pivots) >= 5:
        last5 = pivots[-5:]
        types = "".join(p["type"] for p in last5)

        if types in ("LHLHL", "HLHLH"):
            if last5[-1]["type"] == "L":
                action = "BUY"
                confidence = 73
                wave = "تصحيح هابط مكتمل مبدئياً"
            else:
                action = "SELL"
                confidence = 73
                wave = "موجة صاعدة مكتملة مبدئياً"

    entry, stop, targets = trade_levels(
        klines, action, 1.05, 1.08
    )

    return {
        "analysis": (
            f"🌊 <b>إليوت — {symbol}/USDT</b>\n\n"
            f"القراءة: <b>{wave}</b>\n"
            f"Pivot Count: <b>{len(pivots)}</b>\n"
            f"RSI: <b>{rsi:.1f}</b>\n\n"
            f"التوصية: <b>{action_text(action)}</b>\n"
            f"الثقة: <b>{confidence}%</b>\n\n"
            f"💡 الدخول: {', '.join('$'+str(x) for x in entry)}\n"
            f"🛑 الوقف: ${stop}\n"
            f"🎯 الأهداف: {', '.join('$'+str(x) for x in targets)}\n\n"
            f"⚠️ العد الموجي آلي واحتمالي وليس عدّاً يدوياً مؤكداً."
        ),
        "action": action,
        "confidence": confidence,
        "entry": entry,
        "stop_loss": stop,
        "take_profit": targets,
        "sr": find_sr(klines),
        "school": "elliott",
        "extra": {"pivots": pivots, "wave": wave},
    }


# =========================================================
# SCHOOL 3 — HARMONIC
# =========================================================

def _fib_ratio(a, b, c):
    denominator = abs(a - b)
    return abs(c - b) / denominator if denominator else 0


def harmonic_analysis(klines, symbol):
    pivots = _pivot_points(klines, 3)

    action = "WAIT"
    confidence = 50
    pattern = "لا يوجد نمط هارمونيك مؤكد"

    # Heuristic pattern detection based on four recent pivots.
    # This is deliberately labelled heuristic; it is not a full XABCD solver.
    if len(pivots) >= 4:
        x, a, b, c = pivots[-4:]

        xa = abs(a["price"] - x["price"])
        ab = abs(b["price"] - a["price"])
        bc = abs(c["price"] - b["price"])

        ab_xa = ab / xa if xa else 0
        bc_ab = bc / ab if ab else 0

        if 0.55 <= ab_xa <= 0.68 and 0.35 <= bc_ab <= 0.95:
            pattern = "Gartley/Bat محتمل"
            action = "BUY" if c["price"] < a["price"] else "SELL"
            confidence = 70
        elif 0.70 <= ab_xa <= 0.82:
            pattern = "Butterfly محتمل"
            action = "BUY" if c["price"] < a["price"] else "SELL"
            confidence = 73
        elif 0.80 <= ab_xa <= 0.95:
            pattern = "Crab محتمل"
            action = "BUY" if c["price"] < a["price"] else "SELL"
            confidence = 74

    entry, stop, targets = trade_levels(
        klines, action, 1.05, 1.10
    )

    return {
        "analysis": (
            f"🦋 <b>هارمونيك — {symbol}/USDT</b>\n\n"
            f"النمط: <b>{pattern}</b>\n"
            f"عدد نقاط Pivot: <b>{len(pivots)}</b>\n\n"
            f"التوصية: <b>{action_text(action)}</b>\n"
            f"الثقة: <b>{confidence}%</b>\n\n"
            f"💡 الدخول: {', '.join('$'+str(x) for x in entry)}\n"
            f"🛑 الوقف: ${stop}\n"
            f"🎯 الأهداف: {', '.join('$'+str(x) for x in targets)}\n\n"
            f"⚠️ النمط آلي واحتمالي؛ لا يُعتبر XABCD مؤكداً دون تحقق يدوي."
        ),
        "action": action,
        "confidence": confidence,
        "entry": entry,
        "stop_loss": stop,
        "take_profit": targets,
        "sr": find_sr(klines),
        "school": "harmonic",
        "extra": {"pattern": pattern},
    }


# =========================================================
# SCHOOL 4 — CLASSIC
# =========================================================

def classic_analysis(klines, symbol):
    closes = [k["close"] for k in klines]
    current = closes[-1]

    rsi = calculate_rsi(closes)
    macd = calculate_macd(closes)
    ema20 = calculate_ema(closes, 20)[-1]
    ema50 = calculate_ema(closes, 50)[-1]

    score = 0
    reasons = []

    if current > ema20:
        score += 1
        reasons.append("السعر فوق EMA20")
    else:
        score -= 1
        reasons.append("السعر تحت EMA20")

    if ema20 > ema50:
        score += 1
        reasons.append("EMA20 أعلى EMA50")
    else:
        score -= 1
        reasons.append("EMA20 أسفل EMA50")

    if macd["histogram"] > 0:
        score += 1
        reasons.append("MACD موجب")
    else:
        score -= 1
        reasons.append("MACD سالب")

    if rsi < 30:
        score += 2
        reasons.append("تشبع بيع RSI")
    elif rsi > 70:
        score -= 2
        reasons.append("تشبع شراء RSI")

    if score >= 2:
        action = "BUY"
    elif score <= -2:
        action = "SELL"
    else:
        action = "WAIT"

    confidence = min(90, 50 + abs(score) * 10)

    entry, stop, targets = trade_levels(
        klines, action, 1.04, 1.08
    )

    return {
        "analysis": (
            f"📈 <b>كلاسيكي — {symbol}/USDT</b>\n\n"
            f"RSI: <b>{rsi:.1f}</b>\n"
            f"EMA20: <b>{ema20:.6f}</b>\n"
            f"EMA50: <b>{ema50:.6f}</b>\n"
            f"MACD Histogram: <b>{macd['histogram']:.6f}</b>\n\n"
            f"الأسباب:\n• " + "\n• ".join(reasons) +
            f"\n\nالتوصية: <b>{action_text(action)}</b>\n"
            f"الثقة: <b>{confidence}%</b>\n\n"
            f"💡 الدخول: {', '.join('$'+str(x) for x in entry)}\n"
            f"🛑 الوقف: ${stop}\n"
            f"🎯 الأهداف: {', '.join('$'+str(x) for x in targets)}"
        ),
        "action": action,
        "confidence": confidence,
        "entry": entry,
        "stop_loss": stop,
        "take_profit": targets,
        "sr": find_sr(klines),
        "school": "classic",
        "extra": {"rsi": rsi, "macd": macd},
    }


# =========================================================
# SCHOOL 5 — WHALES
# =========================================================

def whales_analysis(klines, symbol):
    closes = [k["close"] for k in klines]
    volumes = [k["volume"] for k in klines]
    current = closes[-1]

    avg = np.mean(volumes[-50:])
    volume_z = (
        (volumes[-1] - np.mean(volumes[-20:])) /
        (np.std(volumes[-20:]) or 1)
    )

    price_change = (
        (closes[-1] - closes[-5]) / closes[-5] * 100
        if closes[-5] else 0
    )

    # This is market-volume proxy, not blockchain whale tracking.
    if volume_z > 1.5 and price_change > 0:
        action = "BUY"
        confidence = 74
        signal = "حجم استثنائي مع حركة سعرية صاعدة"
    elif volume_z > 1.5 and price_change < 0:
        action = "SELL"
        confidence = 74
        signal = "حجم استثنائي مع حركة سعرية هابطة"
    else:
        action = "WAIT"
        confidence = 50
        signal = "لا يوجد نشاط حجمي استثنائي كافٍ"

    entry, stop, targets = trade_levels(
        klines, action, 1.05, 1.10
    )

    return {
        "analysis": (
            f"🐋 <b>الحيتان — {symbol}/USDT</b>\n\n"
            f"Volume Z-Score: <b>{volume_z:.2f}</b>\n"
            f"تغير السعر 5 شموع: <b>{price_change:.2f}%</b>\n"
            f"المتوسط الحجمي: <b>{avg:.2f}</b>\n\n"
            f"القراءة: <b>{signal}</b>\n"
            f"التوصية: <b>{action_text(action)}</b>\n"
            f"الثقة: <b>{confidence}%</b>\n\n"
            f"💡 الدخول: {', '.join('$'+str(x) for x in entry)}\n"
            f"🛑 الوقف: ${stop}\n"
            f"🎯 الأهداف: {', '.join('$'+str(x) for x in targets)}\n\n"
            f"⚠️ هذا مؤشر حجم سوقي، وليس تتبعاً مباشراً لمحافظ الحيتان على السلسلة."
        ),
        "action": action,
        "confidence": confidence,
        "entry": entry,
        "stop_loss": stop,
        "take_profit": targets,
        "sr": find_sr(klines),
        "school": "whales",
        "extra": {"volume_z": volume_z},
    }


# =========================================================
# SCHOOL 6 — TVL
# =========================================================

def tvl_analysis(klines, symbol):
    closes = [k["close"] for k in klines]
    volumes = [k["volume"] for k in klines]

    current = closes[-1]

    avg30 = np.mean(volumes[-30:])
    avg7 = np.mean(volumes[-7:])
    liquidity_proxy = avg7 / avg30 if avg30 else 1

    trend = (
        (current - closes[-10]) / closes[-10] * 100
        if closes[-10] else 0
    )

    if liquidity_proxy > 1.20 and trend > 0:
        action = "BUY"
        confidence = 69
        signal = "ارتفاع السيولة السوقية مع اتجاه صاعد"
    elif liquidity_proxy < 0.80 and trend < 0:
        action = "SELL"
        confidence = 67
        signal = "انخفاض السيولة السوقية مع اتجاه هابط"
    else:
        action = "WAIT"
        confidence = 50
        signal = "لا توجد موافقة كافية بين السيولة والاتجاه"

    entry, stop, targets = trade_levels(
        klines, action, 1.04, 1.07
    )

    return {
        "analysis": (
            f"🔒 <b>TVL — {symbol}/USDT</b>\n\n"
            f"Liquidity Proxy: <b>{liquidity_proxy:.2f}x</b>\n"
            f"اتجاه السعر: <b>{trend:.2f}%</b>\n\n"
            f"القراءة: <b>{signal}</b>\n"
            f"التوصية: <b>{action_text(action)}</b>\n"
            f"الثقة: <b>{confidence}%</b>\n\n"
            f"💡 الدخول: {', '.join('$'+str(x) for x in entry)}\n"
            f"🛑 الوقف: ${stop}\n"
            f"🎯 الأهداف: {', '.join('$'+str(x) for x in targets)}\n\n"
            f"⚠️ هذه النسخة تستخدم Volume كبديل للسيولة؛ "
            f"TVL الحقيقي يحتاج مزود بيانات DeFi on-chain."
        ),
        "action": action,
        "confidence": confidence,
        "entry": entry,
        "stop_loss": stop,
        "take_profit": targets,
        "sr": find_sr(klines),
        "school": "tvl",
        "extra": {"liquidity_proxy": liquidity_proxy},
    }


def analyze_by_school(klines, symbol, school_id):
    analyzers = {
        "wyckoff": wyckoff_analysis,
        "elliott": elliott_analysis,
        "harmonic": harmonic_analysis,
        "classic": classic_analysis,
        "whales": whales_analysis,
        "tvl": tvl_analysis,
    }

    analyzer = analyzers.get(school_id, classic_analysis)
    return analyzer(klines, symbol)


# =========================================================
# CHARTS
# =========================================================

def create_chart(
    klines: List[Dict],
    symbol: str,
    school_id: str,
    signal: Dict,
) -> io.BytesIO:
    school = TRADING_SCHOOLS[school_id]
    plt.style.use("dark_background")

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    dates = [k["time"] for k in klines]
    opens = [k["open"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    closes = [k["close"] for k in klines]

    # Candles
    for i in range(len(klines)):
        color = "#26a69a" if closes[i] >= opens[i] else "#ef5350"
        ax.plot(
            [dates[i], dates[i]],
            [lows[i], highs[i]],
            color=color,
            linewidth=1,
        )
        ax.plot(
            [dates[i], dates[i]],
            [opens[i], closes[i]],
            color=color,
            linewidth=4,
        )

    # School-specific visual layer
    if school_id == "wyckoff":
        ax.fill_between(
            dates,
            min(lows),
            max(highs),
            alpha=0.03,
        )

    elif school_id == "elliott":
        pivots = signal.get("extra", {}).get("pivots", [])
        px = [
            dates[p["index"]]
            for p in pivots
            if 0 <= p["index"] < len(dates)
        ]
        py = [p["price"] for p in pivots if 0 <= p["index"] < len(dates)]
        if px:
            ax.plot(px, py, linewidth=2, marker="o")

    elif school_id == "harmonic":
        pivots = _pivot_points(klines, 3)[-5:]
        px = [
            dates[p["index"]]
            for p in pivots
            if 0 <= p["index"] < len(dates)
        ]
        py = [p["price"] for p in pivots if 0 <= p["index"] < len(dates)]
        if px:
            ax.plot(px, py, linewidth=2, marker="o")

    elif school_id == "classic":
        ema20 = calculate_ema(closes, 20)
        ema50 = calculate_ema(closes, 50)
        ax.plot(dates, ema20, linewidth=1.5, label="EMA20")
        ax.plot(dates, ema50, linewidth=1.5, label="EMA50")
        ax.legend()

    elif school_id == "whales":
        vol = np.array([k["volume"] for k in klines])
        threshold = np.mean(vol[-50:]) * 1.7
        whale_idx = np.where(vol > threshold)[0]
        for i in whale_idx:
            ax.axvline(dates[i], alpha=0.25, linewidth=1)

    elif school_id == "tvl":
        # Show a normalized volume panel as a visual liquidity proxy
        vol = np.array([k["volume"] for k in klines])
        norm = (vol - vol.min()) / ((vol.max() - vol.min()) or 1)
        bottom = min(lows)
        top = max(highs)
        ax.plot(
            dates,
            bottom + norm * (top - bottom) * 0.15,
            linewidth=1.2,
        )

    # S/R
    for support in signal["sr"]["supports"]:
        ax.axhline(
            y=support,
            linestyle="--",
            alpha=0.55,
            linewidth=1,
        )

    for resistance in signal["sr"]["resistances"]:
        ax.axhline(
            y=resistance,
            linestyle="--",
            alpha=0.55,
            linewidth=1,
        )

    # Entry/SL/TP
    for entry in signal["entry"]:
        ax.axhline(y=entry, linestyle="-", alpha=0.65, linewidth=1)

    ax.axhline(
        y=signal["stop_loss"],
        linestyle="-",
        alpha=0.8,
        linewidth=1.5,
    )

    for tp in signal["take_profit"]:
        ax.axhline(y=tp, linestyle="-", alpha=0.8, linewidth=1.2)

    ax.set_title(
        f"{symbol}/USDT — {school['name']}",
        fontsize=16,
        fontweight="bold",
    )

    ax.grid(True, alpha=0.20)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(
        buf,
        format="png",
        dpi=140,
        facecolor="#0d1117",
    )
    buf.seek(0)
    plt.close(fig)

    return buf


# =========================================================
# KEYBOARDS
# =========================================================

def main_kb():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📊 التحليل الفني",
            callback_data="start_analysis",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💎 الاشتراكات",
            callback_data="plans",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 حالتي",
            callback_data="status",
        ),
        InlineKeyboardButton(
            text="ℹ️ مساعدة",
            callback_data="help",
        ),
    )

    return builder.as_markup()


def back_main_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 الرئيسية",
                    callback_data="back_main",
                )
            ]
        ]
    )


def schools_kb():
    builder = InlineKeyboardBuilder()

    for sid, school in TRADING_SCHOOLS.items():
        builder.row(
            InlineKeyboardButton(
                text=f"{school['emoji']} {school['name']}",
                callback_data=f"school_{sid}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔙 الرئيسية",
            callback_data="back_main",
        )
    )

    return builder.as_markup()


def timeframes_kb(sid):
    builder = InlineKeyboardBuilder()

    for tf in TRADING_SCHOOLS[sid]["timeframes"]:
        builder.row(
            InlineKeyboardButton(
                text=f"⏰ {tf}",
                callback_data=f"tf_{sid}_{tf}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔙 المدارس",
            callback_data="start_analysis",
        )
    )

    return builder.as_markup()


def coins_kb(sid, tf):
    builder = InlineKeyboardBuilder()

    coins = [
        "BTC", "ETH", "SOL", "BNB",
        "XRP", "ADA", "DOGE", "AVAX",
        "LINK", "DOT", "SUI", "TON",
    ]

    for i in range(0, len(coins), 2):
        builder.row(
            *[
                InlineKeyboardButton(
                    text=f"💰 {c}",
                    callback_data=f"analyze_{sid}_{tf}_{c}",
                )
                for c in coins[i:i + 2]
            ]
        )

    builder.row(
        InlineKeyboardButton(
            text="🔍 بحث عن عملة",
            callback_data=f"custom_{sid}_{tf}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 المدرسة",
            callback_data=f"school_{sid}",
        )
    )

    return builder.as_markup()


def analysis_result_kb(sid, tf):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 تحليل جديد",
                    callback_data=f"tf_{sid}_{tf}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏫 تغيير المدرسة",
                    callback_data="start_analysis",
                ),
                InlineKeyboardButton(
                    text="🏠 الرئيسية",
                    callback_data="back_main",
                ),
            ],
        ]
    )


# =========================================================
# START / USER
# =========================================================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await db.upsert_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )

    await message.answer(
        "🌟 <b>Doshka Trading Pro</b>\n\n"
        "📊 6 مدارس تحليل مختلفة\n"
        "🎯 كل مدرسة تستخدم منطقاً مختلفاً\n"
        "💳 الدفع يتم مراقبته تلقائياً بدون إرسال TX Hash\n\n"
        "اختر من القائمة:",
        reply_markup=main_kb(),
    )


@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🌟 <b>Doshka Trading Pro</b>",
        reply_markup=main_kb(),
    )
    await callback.answer()


# =========================================================
# ANALYSIS HANDLERS
# =========================================================

@dp.callback_query(F.data == "start_analysis")
async def start_analysis(callback: CallbackQuery):
    if not await db.is_subscribed(callback.from_user.id):
        await callback.answer(
            "❌ التحليل متاح للمشتركين فقط",
            show_alert=True,
        )
        return

    text = "<b>📊 اختر مدرسة التحليل:</b>\n\n"

    for sid, school in TRADING_SCHOOLS.items():
        text += (
            f"{school['emoji']} <b>{school['name']}</b>\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=schools_kb(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("school_"))
async def choose_school(callback: CallbackQuery):
    sid = callback.data[len("school_"):]

    if sid not in TRADING_SCHOOLS:
        await callback.answer(
            "❌ مدرسة غير معروفة",
            show_alert=True,
        )
        return

    school = TRADING_SCHOOLS[sid]

    await callback.message.edit_text(
        f"{school['emoji']} <b>{school['name']}</b>\n\n"
        f"اختر الفترة الزمنية:",
        reply_markup=timeframes_kb(sid),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("tf_"))
async def choose_tf(callback: CallbackQuery):
    parts = callback.data.split("_", 2)

    if len(parts) != 3:
        await callback.answer("❌ اختيار غير صالح", show_alert=True)
        return

    sid, tf = parts[1], parts[2]

    if sid not in TRADING_SCHOOLS:
        await callback.answer("❌ مدرسة غير صالحة", show_alert=True)
        return

    if tf not in TRADING_SCHOOLS[sid]["timeframes"]:
        await callback.answer("❌ فريم غير صالح", show_alert=True)
        return

    await callback.message.edit_text(
        "💰 <b>اختر العملة:</b>",
        reply_markup=coins_kb(sid, tf),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("custom_"))
async def custom_symbol(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_", 2)

    if len(parts) != 3:
        await callback.answer("❌ اختيار غير صالح", show_alert=True)
        return

    sid, tf = parts[1], parts[2]

    if sid not in TRADING_SCHOOLS:
        await callback.answer("❌ مدرسة غير صالحة", show_alert=True)
        return

    await state.update_data(sid=sid, tf=tf)
    await state.set_state(
        AnalysisStates.waiting_for_custom_symbol
    )

    await callback.message.edit_text(
        "🔍 <b>أدخل رمز العملة</b>\n\n"
        "مثال: <code>BTC</code> أو <code>SOL</code>",
        reply_markup=back_main_kb(),
    )
    await callback.answer()


@dp.message(StateFilter(AnalysisStates.waiting_for_custom_symbol))
async def process_custom(message: Message, state: FSMContext):
    data = await state.get_data()

    sid = data.get("sid")
    tf = data.get("tf")

    symbol = (message.text or "").strip().upper()
    symbol = symbol.replace("/", "").replace("USDT", "")

    await state.clear()

    if sid not in TRADING_SCHOOLS:
        await message.answer("❌ مدرسة غير صالحة", reply_markup=main_kb())
        return

    if not symbol.isalnum() or len(symbol) > 20:
        await message.answer("❌ رمز عملة غير صالح")
        return

    await do_analysis(message, symbol, sid, tf)


@dp.callback_query(F.data.startswith("analyze_"))
async def analyze_cb(callback: CallbackQuery):
    parts = callback.data.split("_", 3)

    if len(parts) != 4:
        await callback.answer("❌ اختيار غير صالح", show_alert=True)
        return

    sid, tf, symbol = parts[1], parts[2], parts[3]

    if not await db.is_subscribed(callback.from_user.id):
        await callback.answer("❌ للمشتركين فقط", show_alert=True)
        return

    await callback.answer("⏳ جاري التحليل...")
    await do_analysis(callback.message, symbol, sid, tf)


async def do_analysis(
    message: Message,
    symbol: str,
    sid: str,
    tf: str,
):
    if not await db.is_subscribed(message.from_user.id):
        await message.answer(
            "❌ تحتاج اشتراكاً فعالاً.",
            reply_markup=main_kb(),
        )
        return

    school_name = TRADING_SCHOOLS[sid]["name"]

    wait = await message.answer(
        f"⏳ جاري تحليل <b>{symbol}/USDT</b>\n"
        f"بالمدرسة: <b>{school_name}</b>"
    )

    klines = await get_klines(symbol, tf, 150)

    if len(klines) < 60:
        await wait.edit_text(
            "❌ البيانات غير كافية أو العملة غير موجودة على Binance."
        )
        return

    try:
        signal = await asyncio.to_thread(
            analyze_by_school,
            klines,
            symbol,
            sid,
        )

        chart = await asyncio.to_thread(
            create_chart,
            klines,
            symbol,
            sid,
            signal,
        )

        await wait.delete()

        await message.answer_photo(
            photo=BufferedInputFile(
                chart.read(),
                filename=f"{symbol}_{sid}_{tf}.png",
            ),
            caption=signal["analysis"],
            reply_markup=analysis_result_kb(sid, tf),
        )

    except Exception as e:
        logger.exception("Analysis error")
        await wait.edit_text(
            f"❌ حدث خطأ أثناء التحليل: {str(e)[:120]}"
        )


# =========================================================
# SUBSCRIPTIONS
# =========================================================

@dp.callback_query(F.data == "plans")
async def show_plans(callback: CallbackQuery):
    text = "<b>💎 خطط الاشتراك</b>\n\n"

    builder = InlineKeyboardBuilder()

    for plan_id, plan in PLANS.items():
        text += (
            f"{plan['emoji']} <b>{plan['name']}</b> — "
            f"${plan['price']:.0f}\n"
        )

        builder.row(
            InlineKeyboardButton(
                text=f"{plan['emoji']} {plan['name']} — ${plan['price']:.0f}",
                callback_data=f"subscribe_{plan_id}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔙 الرئيسية",
            callback_data="back_main",
        )
    )

    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("subscribe_"))
async def subscribe_plan(callback: CallbackQuery):
    plan_id = callback.data[len("subscribe_"):]

    if plan_id not in PLANS:
        await callback.answer("❌ باقة غير صالحة", show_alert=True)
        return

    plan = PLANS[plan_id]

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◎ Solana",
            callback_data=f"net_{plan_id}_sol",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Ξ Ethereum",
            callback_data=f"net_{plan_id}_eth",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🟡 BNB Chain",
            callback_data=f"net_{plan_id}_bnb",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 الاشتراكات",
            callback_data="plans",
        )
    )

    await callback.message.edit_text(
        f"💳 <b>{plan['name']}</b>\n\n"
        f"السعر: <b>${plan['price']:.2f}</b>\n\n"
        f"اختر الشبكة التي تريد الدفع عبرها:",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


NETWORK_NAMES = {
    "sol": "Solana",
    "eth": "Ethereum",
    "bnb": "BNB Smart Chain",
}

NETWORK_SYMBOLS = {
    "sol": "USDT",
    "eth": "USDT",
    "bnb": "USDT",
}

USDT_CONTRACTS = {
    # Official Tether Ethereum USDT contract.
    "eth": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    # Common BNB Smart Chain USDT (BEP-20) contract.
    "bnb": "0x55d398326f99059ff775485246999027b3197955",
    # Official Tether Solana USDT mint.
    "sol": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
}

USDT_DECIMALS = {
    "eth": 6,
    "bnb": 18,
    "sol": 6,
}


@dp.callback_query(F.data.startswith("net_"))
async def choose_network(callback: CallbackQuery):
    parts = callback.data.split("_")

    if len(parts) != 3:
        await callback.answer("❌ اختيار غير صالح", show_alert=True)
        return

    plan_id, network = parts[1], parts[2]

    if plan_id not in PLANS:
        await callback.answer("❌ باقة غير صالحة", show_alert=True)
        return

    if network not in NETWORK_NAMES:
        await callback.answer("❌ شبكة غير صالحة", show_alert=True)
        return

    wallets = {
        "sol": SOL_WALLET,
        "eth": ETH_WALLET,
        "bnb": BNB_WALLET,
    }
    wallet = wallets[network]

    if not wallet:
        await callback.message.edit_text(
            "❌ هذه الشبكة غير مفعلة حالياً.\nتواصل مع الإدارة.",
            reply_markup=back_main_kb(),
        )
        await callback.answer()
        return

    # Invoice is always denominated in USDT: no SOL/ETH/BNB price lookup.
    expected_usdt = float(PLANS[plan_id]["price"])

    intent_id = await db.create_payment_intent(
        callback.from_user.id,
        plan_id,
        network,
        wallet,
        expected_usdt,
        expected_usdt,
        1.0,
    )

    expires = utcnow() + timedelta(hours=PAYMENT_MAX_AGE_HOURS)

    await callback.message.edit_text(
        f"💳 <b>فاتورة الدفع #{intent_id}</b>\n\n"
        f"📦 الباقة: <b>{PLANS[plan_id]['name']}</b>\n"
        f"💵 المبلغ المطلوب: <b>{expected_usdt:.2f} USDT</b>\n"
        f"🌐 الشبكة: <b>{NETWORK_NAMES[network]}</b>\n\n"
        f"🪙 <b>USDT فقط</b>\n"
        f"📮 أرسل إلى:\n<code>{wallet}</code>\n\n"
        f"⏳ الفاتورة صالحة حتى:\n<b>{format_dt(expires)}</b>\n\n"
        "⚠️ تأكد أن الشبكة المختارة مطابقة للشبكة التي سترسل منها USDT.\n"
        "🔎 <b>لا ترسل TX Hash.</b> سيكتشف البوت الدفع تلقائياً.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 تحديث حالة الدفع",
                        callback_data=f"payment_status_{intent_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ إلغاء",
                        callback_data="plans",
                    )
                ],
            ]
        ),
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("payment_status_"))
async def payment_status(callback: CallbackQuery):
    try:
        intent_id = int(callback.data.split("_")[-1])
    except Exception:
        await callback.answer("❌ فاتورة غير صالحة", show_alert=True)
        return

    intent = await db.get_intent(intent_id)

    if not intent or intent["user_id"] != callback.from_user.id:
        await callback.answer(
            "❌ هذه الفاتورة ليست لك",
            show_alert=True,
        )
        return

    if intent["status"] == "paid":
        await callback.message.edit_text(
            "✅ <b>تم العثور على دفعتك وتفعيل الاشتراك.</b>",
            reply_markup=back_main_kb(),
        )
        await callback.answer()
        return

    if intent["status"] == "expired":
        await callback.answer(
            "⌛ انتهت صلاحية الفاتورة",
            show_alert=True,
        )
        return

    await callback.answer(
        "⏳ لم يتم العثور على دفعة مؤكدة بعد. "
        "سيستمر البوت في المراقبة تلقائياً.",
        show_alert=True,
    )


@dp.callback_query(F.data == "status")
async def check_status(callback: CallbackQuery):
    row = await db.get_user_status(callback.from_user.id)

    if not row or not row["expire_date"]:
        text = "❌ <b>لا يوجد اشتراك فعال.</b>"
    else:
        try:
            expire = datetime.fromisoformat(row["expire_date"])
            active = bool(row["is_active"]) and expire > utcnow()
        except Exception:
            active = False
            expire = None

        if active:
            text = (
                "✅ <b>اشتراكك نشط</b>\n\n"
                f"📦 الباقة: <b>{PLANS.get(row['plan'], {}).get('name', row['plan'])}</b>\n"
                f"📅 الانتهاء: <b>{format_dt(expire)}</b>"
            )
        else:
            text = "❌ <b>اشتراكك منتهي أو غير فعال.</b>"

    await callback.message.edit_text(
        text,
        reply_markup=back_main_kb(),
    )
    await callback.answer()


# =========================================================
# HELP
# =========================================================

@dp.callback_query(F.data == "help")
async def help_cb(callback: CallbackQuery):
    text = (
        "<b>📖 Doshka Trading Pro</b>\n\n"
        "📊 <b>وايكوف:</b> الحجم ومراحل التجميع/التوزيع\n"
        "🌊 <b>إليوت:</b> Pivot structure والموجات المحتملة\n"
        "🦋 <b>هارمونيك:</b> نسب Fibonacci وأنماط محتملة\n"
        "📈 <b>كلاسيكي:</b> EMA + RSI + MACD\n"
        "🐋 <b>الحيتان:</b> شذوذ الحجم وحركة السعر\n"
        "🔒 <b>TVL:</b> مؤشر سيولة تقريبي من بيانات السوق\n\n"
        "💳 <b>الدفع:</b>\n"
        "بعد اختيار الشبكة يحصل المستخدم على فاتورة "
        "بكمية محددة من ETH/BNB/SOL.\n"
        "لا يحتاج المستخدم لإرسال Transaction Hash؛ "
        "النظام يبحث عن الدفع تلقائياً.\n\n"
        "⚠️ التحليلات مؤشرات احتمالية وليست ضماناً للربح."
    )

    await callback.message.edit_text(
        text,
        reply_markup=back_main_kb(),
    )
    await callback.answer()


# =========================================================
# AUTOMATIC USDT PAYMENT VERIFICATION
# =========================================================

ERC20_TRANSFER_TOPIC = (
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a"
    "d0f523b3ef"
)


async def get_recent_evm_usdt_transfers(
    network: str,
    wallet: str,
    session: aiohttp.ClientSession,
) -> List[Dict]:
    """Find successful ERC-20/BEP-20 USDT transfers into the configured wallet."""
    if network not in ("eth", "bnb") or not wallet:
        return []

    rpc = ETH_RPC_URL if network == "eth" else BNB_RPC_URL
    contract = USDT_CONTRACTS[network].lower()
    decimals = USDT_DECIMALS[network]

    # topic[1] = from, topic[2] = to. We filter topic[2] ourselves.
    wallet_topic = "0x" + wallet[2:].lower().zfill(64)
    transfers = []

    try:
        latest = await rpc_call(session, rpc, "eth_blockNumber", [])
        if not latest:
            return []

        latest_num = int(latest, 16)
        # Scan a modest recent window on each cycle.
        start_num = max(0, latest_num - 120)
        logs = await rpc_call(
            session,
            rpc,
            "eth_getLogs",
            [{
                "fromBlock": hex(start_num),
                "toBlock": latest,
                "address": contract,
                "topics": [ERC20_TRANSFER_TOPIC, None, wallet_topic],
            }],
        )

        if not logs:
            return []

        for log in logs:
            topics = log.get("topics") or []
            if len(topics) < 3:
                continue

            try:
                raw_amount = int(log.get("data", "0x0"), 16)
                amount_usdt = raw_amount / (10 ** decimals)
            except Exception:
                continue

            if amount_usdt <= 0:
                continue

            tx_hash = log.get("transactionHash")
            if not tx_hash:
                continue

            receipt = await rpc_call(
                session,
                rpc,
                "eth_getTransactionReceipt",
                [tx_hash],
            )
            if not receipt or receipt.get("status") != "0x1":
                continue

            transfers.append({
                "tx_hash": tx_hash,
                "amount_native": amount_usdt,
                "amount_usd": amount_usdt,
                "block": int(log.get("blockNumber", "0x0"), 16),
                "timestamp": 0,
            })

        return transfers

    except Exception as e:
        logger.warning("%s USDT RPC scan failed: %s", network, e)
        return []


async def get_recent_solana_usdt_transfers(
    wallet: str,
    session: aiohttp.ClientSession,
) -> List[Dict]:
    """Find successful SPL-USDT transfers into the configured Solana wallet."""
    if not wallet:
        return []

    mint = USDT_CONTRACTS["sol"]
    decimals = USDT_DECIMALS["sol"]

    try:
        token_accounts = await rpc_call(
            session,
            SOL_RPC_URL,
            "getTokenAccountsByOwner",
            [
                wallet,
                {"mint": mint},
                {"encoding": "jsonParsed"},
            ],
        )

        values = (token_accounts or {}).get("value", [])
        if not values:
            return []

        transfers = []
        seen = set()

        for item in values:
            token_account = ((item.get("pubkey") or "").strip())
            if not token_account:
                continue

            signatures = await rpc_call(
                session,
                SOL_RPC_URL,
                "getSignaturesForAddress",
                [
                    token_account,
                    {"limit": 30, "commitment": "confirmed"},
                ],
            ) or []

            for sig_item in signatures:
                signature = sig_item.get("signature")
                if not signature or signature in seen or sig_item.get("err") is not None:
                    continue
                seen.add(signature)

                tx = await rpc_call(
                    session,
                    SOL_RPC_URL,
                    "getTransaction",
                    [
                        signature,
                        {
                            "encoding": "jsonParsed",
                            "maxSupportedTransactionVersion": 0,
                            "commitment": "confirmed",
                        },
                    ],
                )

                if not tx or (tx.get("meta") or {}).get("err") is not None:
                    continue

                meta = tx.get("meta") or {}
                post_balances = meta.get("postTokenBalances") or []
                pre_balances = meta.get("preTokenBalances") or []

                pre_by_account = {}
                for b in pre_balances:
                    if b.get("mint") == mint and b.get("owner") == wallet:
                        idx = b.get("accountIndex")
                        amount = ((b.get("uiTokenAmount") or {}).get("amount"))
                        if idx is not None and amount is not None:
                            pre_by_account[idx] = int(amount)

                delta_total = 0
                for b in post_balances:
                    if b.get("mint") != mint or b.get("owner") != wallet:
                        continue
                    idx = b.get("accountIndex")
                    amount = ((b.get("uiTokenAmount") or {}).get("amount"))
                    if idx is None or amount is None:
                        continue
                    delta_total += int(amount) - pre_by_account.get(idx, 0)

                if delta_total <= 0:
                    continue

                amount_usdt = delta_total / (10 ** decimals)
                transfers.append({
                    "tx_hash": signature,
                    "amount_native": amount_usdt,
                    "amount_usd": amount_usdt,
                    "block": tx.get("slot", 0),
                    "timestamp": tx.get("blockTime") or 0,
                })

        return transfers

    except Exception as e:
        logger.warning("Solana USDT scan failed: %s", e)
        return []


async def notify_payment_success(
    intent: sqlite3.Row,
    tx_hash: str,
    amount_native: float,
    amount_usd: float,
):
    try:
        expire = await db.activate_subscription(
            intent["user_id"],
            intent["plan"],
        )

        network = NETWORK_NAMES[intent["network"]]

        await bot.send_message(
            intent["user_id"],
            (
                "🎉 <b>تم اكتشاف دفعة USDT وتفعيل الاشتراك!</b>\n\n"
                f"📦 الباقة: <b>{PLANS[intent['plan']]['name']}</b>\n"
                f"🌐 الشبكة: <b>{network}</b>\n"
                f"💰 المبلغ: <b>{amount_native:.6f} USDT</b>\n"
                f"📅 ينتهي: <b>{expire}</b>\n\n"
                f"🔗 TX:\n<code>{tx_hash}</code>\n\n"
                "✅ يمكنك الآن استخدام التحليل."
            ),
        )

        await bot.send_message(
            ADMIN_ID,
            (
                "💰 <b>دفعة USDT جديدة</b>\n\n"
                f"👤 User ID: <code>{intent['user_id']}</code>\n"
                f"📦 الباقة: {PLANS[intent['plan']]['name']}\n"
                f"🌐 الشبكة: {network}\n"
                f"💰 المبلغ: {amount_native:.6f} USDT\n"
                f"🔗 TX: <code>{tx_hash}</code>"
            ),
        )

    except Exception:
        logger.exception("Payment notification failed")


async def scan_payment_group(
    network: str,
    wallet: str,
    intents: List[sqlite3.Row],
    session: aiohttp.ClientSession,
):
    if network in ("eth", "bnb"):
        transfers = await get_recent_evm_usdt_transfers(
            network, wallet, session
        )
    else:
        transfers = await get_recent_solana_usdt_transfers(
            wallet, session
        )

    if not transfers:
        return

    transfers.sort(
        key=lambda x: (x.get("timestamp", 0), x.get("block", 0))
    )

    for intent in intents:
        expected = float(intent["expected_native"])
        minimum = max(0.0, expected - PAYMENT_TOLERANCE_USDT)

        for transfer in transfers:
            tx_hash = transfer.get("tx_hash")
            amount_usdt = safe_float(transfer.get("amount_native"))

            if not tx_hash or amount_usdt < minimum:
                continue

            # Prevent a single transfer from paying two invoices.
            if await db.intent_has_tx(tx_hash):
                continue

            completed = await db.complete_payment(
                intent["id"],
                tx_hash,
                amount_usdt,
                amount_usdt,
            )

            if completed:
                await notify_payment_success(
                    intent,
                    tx_hash,
                    amount_usdt,
                    amount_usdt,
                )
                break


async def payment_monitor():
    """Background worker: automatically watches USDT transfers."""
    logger.info(
        "Automatic USDT payment monitor started: every %ss",
        PAYMENT_SCAN_SECONDS,
    )

    timeout = aiohttp.ClientTimeout(total=45)

    while True:
        try:
            intents = await db.get_pending_intents()

            if intents:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    grouped = {}

                    for intent in intents:
                        key = (intent["network"], intent["wallet"])
                        grouped.setdefault(key, []).append(intent)

                    for (network, wallet), group in grouped.items():
                        try:
                            await scan_payment_group(
                                network, wallet, group, session
                            )
                        except Exception:
                            logger.exception(
                                "USDT payment scan failed: %s/%s",
                                network,
                                wallet,
                            )

        except asyncio.CancelledError:
            logger.info("Payment monitor cancelled")
            raise
        except Exception:
            logger.exception("Payment monitor loop error")

        await asyncio.sleep(PAYMENT_SCAN_SECONDS)


# =========================================================
# STARTUP
# =========================================================

async def main():
    await db.init()

    monitor_task = asyncio.create_task(
        payment_monitor(),
        name="payment-monitor",
    )

    try:
        logger.info("🚀 Doshka Trading Pro is running")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        monitor_task.cancel()

        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
