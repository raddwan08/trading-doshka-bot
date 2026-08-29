"""
Doshka Trading Pro — Telegram Bot
نسخة احترافية جاهزة لـ Railway + دفع حقيقي + كل الأوامر
"""

import asyncio
import os
import re
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import aiohttp
import asyncpg
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

load_dotenv()

# ====================== الإعدادات ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
SOL_WALLET = os.getenv("SOL_WALLET", "GXrqH3WvjSSq6vfufU39oPYKDsracPnVe7sLm2rEBniJ")
BNB_ETH_WALLET = os.getenv("BNB_ETH_WALLET", "0xF79A1bEc46037dcA06077889F4bb1A111B67723e").lower()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")
SOLANA_RPC = os.getenv("SOLANA_RPC", "https://api.mainnet-beta.solana.com")
DATABASE_URL = os.getenv("DATABASE_URL")  # Postgres
SQLITE_PATH = os.getenv("SQLITE_PATH", "data/subscriptions.db")
PAYMENT_TOLERANCE = float(os.getenv("PAYMENT_TOLERANCE", "0.12"))  # 12%

if not BOT_TOKEN or not ADMIN_ID:
    raise SystemExit("❌ BOT_TOKEN و ADMIN_ID مطلوبان في .env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("doshka")

PLANS = {
    "1m": {"days": 30, "price": 20, "name": "شهر واحد"},
    "3m": {"days": 90, "price": 50, "name": "3 أشهر"},
    "6m": {"days": 180, "price": 75, "name": "6 أشهر"},
    "1y": {"days": 365, "price": 125, "name": "سنة كاملة"},
}

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ====================== قاعدة البيانات ======================
pool: Optional[asyncpg.Pool] = None
use_postgres = bool(DATABASE_URL)

async def init_db():
    global pool
    if use_postgres:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    plan TEXT,
                    start_date TIMESTAMPTZ,
                    expire_date TIMESTAMPTZ,
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS used_hashes (
                    tx_hash TEXT PRIMARY KEY,
                    user_id BIGINT,
                    plan TEXT,
                    network TEXT,
                    amount_usd NUMERIC,
                    used_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS favorites (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    symbol TEXT,
                    added_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(user_id, symbol)
                );
                CREATE TABLE IF NOT EXISTS pending_payments (
                    user_id BIGINT,
                    plan TEXT,
                    network TEXT,
                    expected_crypto NUMERIC,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (user_id, plan, network)
                );
            """)
            await conn.execute(
                "INSERT INTO users (user_id, is_active, plan) VALUES ($1, TRUE, 'admin') "
                "ON CONFLICT (user_id) DO NOTHING", ADMIN_ID
            )
        logger.info("✅ Postgres جاهز")
    else:
        import sqlite3
        os.makedirs(os.path.dirname(SQLITE_PATH) or ".", exist_ok=True)
        conn = sqlite3.connect(SQLITE_PATH)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, plan TEXT,
            start_date TEXT, expire_date TEXT, is_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS used_hashes (
            tx_hash TEXT PRIMARY KEY, user_id INTEGER, plan TEXT, network TEXT,
            amount_usd REAL, used_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, symbol TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, symbol))""")
        c.execute("""CREATE TABLE IF NOT EXISTS pending_payments (
            user_id INTEGER, plan TEXT, network TEXT, expected_crypto REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, plan, network))""")
        c.execute("INSERT OR IGNORE INTO users (user_id, is_active, plan) VALUES (?,1,'admin')", (ADMIN_ID,))
        conn.commit()
        conn.close()
        logger.info(f"✅ SQLite جاهز: {SQLITE_PATH}")


def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID


async def is_subscribed(uid: int) -> bool:
    if is_admin(uid):
        return True
    if use_postgres:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT expire_date FROM users WHERE user_id=$1 AND is_active=TRUE", uid
            )
            if not row or not row["expire_date"]:
                return False
            return row["expire_date"] > datetime.utcnow().replace(tzinfo=row["expire_date"].tzinfo)
    else:
        import sqlite3
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT expire_date FROM users WHERE user_id=? AND is_active=1", (uid,)
        ).fetchone()
        conn.close()
        if not row or not row["expire_date"]:
            return False
        return datetime.fromisoformat(row["expire_date"]) > datetime.now()


async def activate_sub(uid: int, plan: str, username: str = None, full_name: str = None) -> str:
    expire = datetime.utcnow() + timedelta(days=PLANS[plan]["days"])
    if use_postgres:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, username, full_name, plan, start_date, expire_date, is_active)
                VALUES ($1,$2,$3,$4,NOW(),$5,TRUE)
                ON CONFLICT (user_id) DO UPDATE SET
                    plan=EXCLUDED.plan, start_date=NOW(), expire_date=EXCLUDED.expire_date,
                    is_active=TRUE, username=EXCLUDED.username, full_name=EXCLUDED.full_name
            """, uid, username, full_name, plan, expire)
    else:
        import sqlite3
        conn = sqlite3.connect(SQLITE_PATH)
        conn.execute("""
            INSERT INTO users (user_id,username,full_name,plan,start_date,expire_date,is_active)
            VALUES (?,?,?,?,?,?,1)
            ON CONFLICT(user_id) DO UPDATE SET plan=excluded.plan, start_date=excluded.start_date,
            expire_date=excluded.expire_date, is_active=1, username=excluded.username, full_name=excluded.full_name
        """, (uid, username, full_name, plan, datetime.now().isoformat(), expire.isoformat()))
        conn.commit()
        conn.close()
    return expire.strftime("%Y-%m-%d")


async def is_hash_used(tx: str) -> bool:
    tx = tx.lower().strip()
    if use_postgres:
        async with pool.acquire() as conn:
            return bool(await conn.fetchval("SELECT 1 FROM used_hashes WHERE tx_hash=$1", tx))
    else:
        import sqlite3
        conn = sqlite3.connect(SQLITE_PATH)
        res = conn.execute("SELECT 1 FROM used_hashes WHERE tx_hash=?", (tx,)).fetchone()
        conn.close()
        return bool(res)


async def mark_hash(tx: str, uid: int, plan: str, network: str, amount_usd: float = 0):
    tx = tx.lower().strip()
    if use_postgres:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO used_hashes (tx_hash,user_id,plan,network,amount_usd) VALUES ($1,$2,$3,$4,$5)",
                tx, uid, plan, network, amount_usd
            )
    else:
        import sqlite3
        conn = sqlite3.connect(SQLITE_PATH)
        conn.execute(
            "INSERT INTO used_hashes (tx_hash,user_id,plan,network,amount_usd) VALUES (?,?,?,?,?)",
            (tx, uid, plan, network, amount_usd)
        )
        conn.commit()
        conn.close()


async def add_favorite(uid: int, symbol: str) -> bool:
    symbol = symbol.upper().strip()
    try:
        if use_postgres:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO favorites (user_id, symbol) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                    uid, symbol
                )
        else:
            import sqlite3
            conn = sqlite3.connect(SQLITE_PATH)
            conn.execute("INSERT INTO favorites (user_id,symbol) VALUES (?,?)", (uid, symbol))
            conn.commit()
            conn.close()
        return True
    except Exception:
        return False


async def remove_favorite(uid: int, symbol: str) -> bool:
    symbol = symbol.upper().strip()
    if use_postgres:
        async with pool.acquire() as conn:
            res = await conn.execute(
                "DELETE FROM favorites WHERE user_id=$1 AND symbol=$2", uid, symbol
            )
            return res != "DELETE 0"
    else:
        import sqlite3
        conn = sqlite3.connect(SQLITE_PATH)
        cur = conn.execute("DELETE FROM favorites WHERE user_id=? AND symbol=?", (uid, symbol))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted


async def get_favorites(uid: int) -> list:
    if use_postgres:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT symbol FROM favorites WHERE user_id=$1 ORDER BY added_at DESC", uid
            )
            return [r["symbol"] for r in rows]
    else:
        import sqlite3
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT symbol FROM favorites WHERE user_id=? ORDER BY added_at DESC", (uid,)
        ).fetchall()
        conn.close()
        return [r["symbol"] for r in rows]


# ====================== أسعار العملات ======================
async def get_crypto_price(symbol: str) -> Optional[float]:
    """جلب السعر الحالي بالدولار (CoinGecko)"""
    mapping = {"sol": "solana", "bnb": "binancecoin", "eth": "ethereum"}
    coin_id = mapping.get(symbol.lower())
    if not coin_id:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
                return float(data[coin_id]["usd"])
    except Exception as e:
        logger.error(f"Price fetch error: {e}")
        return None


# ====================== التحقق الحقيقي من الدفع ======================
async def verify_solana_tx(tx_hash: str, expected_usd: float) -> tuple[bool, str, float]:
    """
    يتحقق من معاملة Solana:
    - موجودة ومؤكدة
    - فيها تحويل إلى محفظتنا
    - المبلغ ≈ السعر المطلوب
    """
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [
                    tx_hash,
                    {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0, "commitment": "confirmed"}
                ]
            }
            async with session.post(SOLANA_RPC, json=payload, timeout=15) as resp:
                data = await resp.json()

            if "error" in data or not data.get("result"):
                return False, "المعاملة غير موجودة أو غير مؤكدة بعد", 0.0

            result = data["result"]
            if result.get("meta", {}).get("err"):
                return False, "المعاملة فشلت على الشبكة", 0.0

            # استخراج التحويلات
            pre = result["meta"].get("preBalances", [])
            post = result["meta"].get("postBalances", [])
            account_keys = [k["pubkey"] if isinstance(k, dict) else k for k in result["transaction"]["message"]["accountKeys"]]

            sol_received = 0.0
            for i, key in enumerate(account_keys):
                if key == SOL_WALLET and i < len(pre) and i < len(post):
                    delta = (post[i] - pre[i]) / 1e9  # lamports → SOL
                    if delta > 0:
                        sol_received += delta

            if sol_received <= 0:
                # جرب parsed instructions
                for ix in result["transaction"]["message"].get("instructions", []):
                    parsed = ix.get("parsed")
                    if parsed and parsed.get("type") == "transfer":
                        info = parsed.get("info", {})
                        if info.get("destination") == SOL_WALLET:
                            sol_received += float(info.get("lamports", 0)) / 1e9

            if sol_received <= 0:
                return False, "لم يتم العثور على تحويل إلى محفظة البوت", 0.0

            price = await get_crypto_price("sol")
            if not price:
                return False, "تعذر جلب سعر SOL حالياً، حاول لاحقاً", 0.0

            usd_value = sol_received * price
            min_ok = expected_usd * (1 - PAYMENT_TOLERANCE)
            if usd_value < min_ok:
                return False, f"المبلغ المستلم \( {usd_value:.2f} أقل من المطلوب ( \){expected_usd})", usd_value

            return True, f"✅ تم استلام {sol_received:.4f} SOL ≈ ${usd_value:.2f}", usd_value

    except Exception as e:
        logger.exception("Solana verify error")
        return False, f"خطأ في التحقق: {str(e)[:80]}", 0.0


async def verify_evm_tx(tx_hash: str, network: str, expected_usd: float) -> tuple[bool, str, float]:
    """
    تحقق من معاملة ETH أو BNB باستخدام Explorer API أو RPC
    """
    tx_hash = tx_hash.lower().strip()
    if not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash

    is_bnb = network == "bnb"
    api_key = BSCSCAN_API_KEY if is_bnb else ETHERSCAN_API_KEY
    base = "https://api.bscscan.com/api" if is_bnb else "https://api.etherscan.io/api"
    symbol = "bnb" if is_bnb else "eth"
    chain_name = "BNB" if is_bnb else "ETH"

    try:
        async with aiohttp.ClientSession() as session:
            # أولاً: جلب تفاصيل المعاملة
            params = {
                "module": "proxy",
                "action": "eth_getTransactionByHash",
                "txhash": tx_hash,
                "apikey": api_key or "YourApiKeyToken"
            }
            async with session.get(base, params=params, timeout=12) as resp:
                data = await resp.json()

            result = data.get("result")
            if not result or result == "null":
                return False, f"المعاملة غير موجودة على شبكة {chain_name}", 0.0

            to_addr = (result.get("to") or "").lower()
            if to_addr != BNB_ETH_WALLET:
                return False, f"المعاملة لم تُرسل إلى محفظة البوت ({BNB_ETH_WALLET[:10]}...)", 0.0

            value_wei = int(result.get("value", "0x0"), 16)
            amount = value_wei / 1e18

            if amount <= 0:
                return False, "لا يوجد مبلغ محول في المعاملة", 0.0

            # تأكيد الاستلام (receipt)
            params2 = {
                "module": "proxy",
                "action": "eth_getTransactionReceipt",
                "txhash": tx_hash,
                "apikey": api_key or "YourApiKeyToken"
            }
            async with session.get(base, params=params2, timeout=12) as resp2:
                receipt = await resp2.json()
            status = (receipt.get("result") or {}).get("status")
            if status and status != "0x1":
                return False, "المعاملة فشلت (reverted)", 0.0

            price = await get_crypto_price(symbol)
            if not price:
                return False, f"تعذر جلب سعر {symbol.upper()}", 0.0

            usd_value = amount * price
            min_ok = expected_usd * (1 - PAYMENT_TOLERANCE)
            if usd_value < min_ok:
                return False, f"المبلغ المستلم \( {usd_value:.2f} أقل من المطلوب ( \){expected_usd})", usd_value

            return True, f"✅ تم استلام {amount:.6f} {symbol.upper()} ≈ ${usd_value:.2f}", usd_value

    except Exception as e:
        logger.exception(f"{network} verify error")
        return False, f"خطأ في التحقق: {str(e)[:80]}", 0.0


# ====================== بيانات السوق والتحليل ======================
async def get_coin_data(symbol: str) -> dict:
    symbol = symbol.lower().strip()
    result = {"found": False}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.coingecko.com/api/v3/search?query={symbol}", timeout=10) as resp:
                search = await resp.json()
                coins = search.get("coins", [])
                if not coins:
                    return result
                coin_id = coins[0]["id"]
                name = coins[0]["name"]
                symbol_real = coins[0]["symbol"].upper()

            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&community_data=false&developer_data=false"
            async with session.get(url, timeout=12) as resp:
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
                "change_7d": market.get("price_change_percentage_7d"),
                "high_24h": market.get("high_24h", {}).get("usd"),
                "low_24h": market.get("low_24h", {}).get("usd"),
                "description": (data.get("description", {}).get("en") or "")[:300],
            })
    except Exception as e:
        result["error"] = str(e)
    return result


def format_number(n):
    if n is None:
        return "غير متوفر"
    try:
        n = float(n)
        if n >= 1_000_000_000_000:
            return f"{n/1_000_000_000_000:.2f}T"
        if n >= 1_000_000_000:
            return f"{n/1_000_000_000:.2f}B"
        if n >= 1_000_000:
            return f"{n/1_000_000:.2f}M"
        if n >= 1_000:
            return f"{n/1_000:.2f}K"
        return f"{n:,.2f}"
    except Exception:
        return str(n)


async def get_market_overview() -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/global", timeout=10) as resp:
                data = await resp.json()
            g = data.get("data", {})
            mcap = g.get("total_market_cap", {}).get("usd", 0)
            vol = g.get("total_volume", {}).get("usd", 0)
            btc_dom = g.get("market_cap_percentage", {}).get("btc", 0)
            eth_dom = g.get("market_cap_percentage", {}).get("eth", 0)
            change = g.get("market_cap_change_percentage_24h_usd", 0)
            coins = g.get("active_cryptocurrencies", 0)

            # Top coins
            async with session.get(
                "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=5&page=1",
                timeout=10
            ) as resp2:
                top = await resp2.json()

            lines = [
                f"<b>📊 نظرة عامة على السوق</b>\n",
                f"💰 القيمة السوقية الكلية: <b>${format_number(mcap)}</b>",
                f"🔄 حجم 24 ساعة: <b>${format_number(vol)}</b>",
                f"📈 التغير 24س: <b>{change:+.2f}%</b>",
                f"₿ هيمنة بيتكوين: <b>{btc_dom:.1f}%</b>",
                f"Ξ هيمنة إيثريوم: <b>{eth_dom:.1f}%</b>",
                f"🪙 عدد العملات النشطة: <b>{coins:,}</b>\n",
                "<b>🔝 أفضل 5 عملات:</b>"
            ]
            for c in top:
                ch = c.get("price_change_percentage_24h") or 0
                emoji = "🟢" if ch >= 0 else "🔴"
                lines.append(
                    f"{emoji} <b>{c['symbol'].upper()}</b> ${c['current_price']:,.4f} ({ch:+.2f}%)"
                )
            return "\n".join(lines)
    except Exception as e:
        return f"❌ تعذر جلب بيانات السوق: {e}"


async def get_tvl(protocol: str = None) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            if protocol:
                async with session.get(f"https://api.llama.fi/tvl/{protocol.lower()}", timeout=10) as resp:
                    if resp.status != 200:
                        return f"❌ لم أجد بروتوكول باسم <b>{protocol}</b>\nجرب: aave, uniswap, lido, makerdao..."
                    tvl = await resp.json()
                    return (
                        f"<b>🔒 TVL — {protocol.upper()}</b>\n\n"
                        f"إجمالي القيمة المقفلة: <b>${format_number(tvl)}</b>\n"
                        f"المصدر: DefiLlama"
                    )
            else:
                async with session.get("https://api.llama.fi/v2/chains", timeout=12) as resp:
                    chains = await resp.json()
                chains = sorted(chains, key=lambda x: x.get("tvl", 0), reverse=True)[:10]
                lines = ["<b>🔒 أعلى 10 شبكات حسب TVL</b>\n"]
                for i, c in enumerate(chains, 1):
                    lines.append(f"{i}. <b>{c['name']}</b> — ${format_number(c.get('tvl'))}")
                lines.append("\nلبروتوكول محدد: <code>/tvl aave</code>")
                return "\n".join(lines)
    except Exception as e:
        return f"❌ خطأ في جلب TVL: {e}"


async def get_binance_klines(symbol: str, interval: str = "4h", limit: int = 50) -> list:
    """جلب شموع من Binance (مجاني)"""
    try:
        pair = f"{symbol.upper()}USDT"
        url = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval={interval}&limit={limit}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return [
                    {
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                        "time": k[0]
                    }
                    for k in data
                ]
    except Exception:
        return []


def simple_wyckoff(klines: list) -> str:
    if len(klines) < 20:
        return "بيانات غير كافية للتحليل."
    closes = [k["close"] for k in klines]
    volumes = [k["volume"] for k in klines]
    recent = closes[-10:]
    vol_recent = volumes[-10:]
    trend = "صاعد" if recent[-1] > recent[0] else "هابط"
    avg_vol = sum(volumes[:-10]) / max(len(volumes[:-10]), 1)
    high_vol = sum(1 for v in vol_recent if v > avg_vol * 1.3)

    phase = "توزيع / ضعف" if trend == "هابط" and high_vol > 3 else \
            "تجميع محتمل" if trend == "صاعد" and high_vol > 2 else \
            "تذبذب / مرحلة انتقالية"

    return (
        f"<b>📐 تحليل وايكوف (مبسط)</b>\n\n"
        f"الاتجاه القصير: <b>{trend}</b>\n"
        f"المرحلة المقدرة: <b>{phase}</b>\n"
        f"حجم مرتفع في آخر 10 شموع: {high_vol}/10\n\n"
        f"<i>ملاحظة: هذا تحليل آلي مبسط وليس توصية استثمارية.</i>"
    )


def simple_elliott(klines: list) -> str:
    if len(klines) < 30:
        return "بيانات غير كافية."
    closes = [k["close"] for k in klines[-30:]]
    swings = []
    for i in range(2, len(closes)-2):
        if closes[i] > closes[i-1] and closes[i] > closes[i+1]:
            swings.append(("H", closes[i], i))
        elif closes[i] < closes[i-1] and closes[i] < closes[i+1]:
            swings.append(("L", closes[i], i))

    if len(swings) < 3:
        return "لم يتم اكتشاف موجات واضحة حالياً."

    last_swings = swings[-5:]
    pattern = " → ".join([s[0] for s in last_swings])
    return (
        f"<b>🌊 إليوت ويف (مبسط)</b>\n\n"
        f"آخر التموجات المكتشفة: <code>{pattern}</code>\n"
        f"عدد التموجات الحديثة: {len(last_swings)}\n\n"
        f"السعر الحالي قريب من {'قمة' if last_swings[-1][0]=='H' else 'قاع'} محتملة.\n\n"
        f"<i>تحليل آلي تقريبي — إليوت يحتاج خبرة بشرية.</i>"
    )


def simple_harmonic(klines: list) -> str:
    if len(klines) < 20:
        return "بيانات غير كافية."
    closes = [k["close"] for k in klines]
    high = max(closes[-20:])
    low = min(closes[-20:])
    current = closes[-1]
    retrace = (high - current) / (high - low) if high != low else 0

    pattern = "لا يوجد نمط توافقي واضح"
    if 0.382 <= retrace <= 0.5:
        pattern = "تصحيح محتمل (0.382-0.5) — منطقة اهتمام"
    elif 0.618 <= retrace <= 0.786:
        pattern = "تصحيح عميق (Golden/0.786) — مراقبة انعكاس"

    return (
        f"<b>🦋 الأنماط التوافقية (مبسط)</b>\n\n"
        f"أعلى سعر (20 شمعة): ${high:,.4f}\n"
        f"أدنى سعر: ${low:,.4f}\n"
        f"التصحيح الحالي: <b>{retrace*100:.1f}%</b>\n"
        f"التقدير: {pattern}\n\n"
        f"<i>الأنماط التوافقية الدقيقة تحتاج نقاط XABCD يدوية.</i>"
    )


# ====================== لوحات المفاتيح ======================
def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 الاشتراكات VIP", callback_data="plans")],
        [
            InlineKeyboardButton(text="📈 Spot", callback_data="spot"),
            InlineKeyboardButton(text="🚀 Futures", callback_data="futures")
        ],
        [InlineKeyboardButton(text="⭐ المفضلة", callback_data="favorites")],
        [InlineKeyboardButton(text="📊 تحليل أساسي", callback_data="fundamental")],
        [InlineKeyboardButton(text="📋 حالة اشتراكي", callback_data="status")],
        [InlineKeyboardButton(text="ℹ️ مساعدة", callback_data="help")]
    ])


def back_kb(cb="back_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data=cb)]
    ])


# ====================== الأوامر والأزرار ======================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    name = message.from_user.first_name or "صديق"
    text = (
        f"مرحباً <b>{name}</b>\n\n"
        f"<b>Doshka Trading Pro</b>\n"
        f"إشارات + تحليل أساسي حقيقي + On-chain\n\n"
        f"اختر من القائمة:"
    )
    await message.answer(text, reply_markup=main_kb())


@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    await callback.message.edit_text(
        f"مرحباً <b>{callback.from_user.first_name}</b>\n\n"
        f"<b>Doshka Trading Pro</b>\n"
        f"إشارات + تحليل أساسي حقيقي + On-chain",
        reply_markup=main_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "help")
@dp.message(Command("help"))
async def cmd_help(event: Message | CallbackQuery):
    text = (
        "<b>📖 أوامر البوت</b>\n\n"
        "<b>عامة:</b>\n"
        "/start — القائمة الرئيسية\n"
        "/help — هذه الرسالة\n"
        "/status — حالة الاشتراك\n"
        "/market — نظرة عامة على السوق\n\n"
        "<b>تحليل (للمشتركين):</b>\n"
        "/analyze BTC — تحليل أساسي\n"
        "/wyckoff BTC — تحليل وايكوف\n"
        "/elliott ETH — إليوت ويف\n"
        "/harmonic SOL — أنماط توافقية\n"
        "/tvl — أعلى TVL أو /tvl aave\n"
        "/whales — نشاط الحيتان (ملخص)\n\n"
        "<b>المفضلة:</b>\n"
        "/add BTC — إضافة\n"
        "/remove BTC — حذف\n\n"
        "<b>الاشتراك:</b>\n"
        "من زر 💎 الاشتراكات VIP ثم ادفع وتحقق بـ:\n"
        "<code>/verify 1m sol TX_HASH</code>"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb())
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_kb())


@dp.callback_query(F.data == "status")
@dp.message(Command("status"))
async def cmd_status(event: Message | CallbackQuery):
    uid = event.from_user.id
    active = await is_subscribed(uid)
    if active:
        text = "✅ <b>اشتراكك نشط</b>\nاستمتع بكل الميزات."
    else:
        text = "❌ <b>لا يوجد اشتراك نشط</b>\nاضغط على 💎 الاشتراكات VIP للتفعيل."
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb())
        await event.answer()
    else:
        await event.answer(text)


@dp.callback_query(F.data == "fundamental")
async def fundamental_menu(callback: CallbackQuery):
    if not await is_subscribed(callback.from_user.id):
        await callback.answer("❌ هذا القسم للمشتركين فقط", show_alert=True)
        return
    await callback.message.edit_text(
        "<b>📊 التحليل الأساسي</b>\n\n"
        "أرسل رمز العملة مباشرة مثل:\n"
        "<code>BTC</code> أو <code>ETH</code> أو <code>SOL</code>\n\n"
        "أو استخدم: <code>/analyze BTC</code>\n\n"
        "سأجلب: الترتيب • السعر • القيمة السوقية • العرض • التغير",
        reply_markup=back_kb()
    )
    await callback.answer()


@dp.message(Command("analyze"))
async def cmd_analyze(message: Message, command: CommandObject):
    if not await is_subscribed(message.from_user.id):
        await message.reply("❌ هذا الأمر للمشتركين فقط")
        return
    if not command.args:
        await message.reply("مثال: <code>/analyze BTC</code>")
        return
    await do_analyze(message, command.args.strip().upper())


@dp.message(F.text.regexp(r"^[A-Za-z0-9]{1,12}$"))
async def analyze_by_text(message: Message):
    if not await is_subscribed(message.from_user.id):
        return
    # تجنب الأوامر
    if message.text.startswith("/"):
        return
    await do_analyze(message, message.text.strip().upper())


async def do_analyze(message: Message, symbol: str):
    wait = await message.reply(f"⏳ جاري تحليل <b>{symbol}</b>...")
    data = await get_coin_data(symbol)
    if not data.get("found"):
        await wait.edit_text(f"❌ لم أجد بيانات لـ <b>{symbol}</b>")
        return

    ch24 = data.get("change_24h") or 0
    ch7 = data.get("change_7d") or 0
    ath_ch = data.get("ath_change") or 0
    text = (
        f"<b>📊 تحليل {data['name']} ({data['symbol']})</b>\n"
        f"المصدر: CoinGecko\n\n"
        f"🏆 الترتيب العالمي: <b>#{data['rank'] or 'N/A'}</b>\n"
        f"💵 السعر: <b>${data['price']:,.6f}</b>\n"
        f"📈 القيمة السوقية: <b>${format_number(data['market_cap'])}</b>\n"
        f"🔄 حجم 24 ساعة: <b>${format_number(data['volume_24h'])}</b>\n\n"
        f"📦 العرض المتداول: <b>{format_number(data['circulating'])}</b>\n"
        f"📦 إجمالي العرض: <b>{format_number(data['total_supply'])}</b>\n"
        f"📦 أقصى عرض: <b>{format_number(data['max_supply'])}</b>\n\n"
        f"📉 من ATH: <b>{ath_ch:.1f}%</b>\n"
        f"📊 التغير 24س: <b>{ch24:+.2f}%</b>\n"
        f"📊 التغير 7 أيام: <b>{ch7:+.2f}%</b>"
    )
    await wait.edit_text(text)


@dp.message(Command("market"))
async def cmd_market(message: Message):
    wait = await message.reply("⏳ جاري جلب بيانات السوق...")
    text = await get_market_overview()
    await wait.edit_text(text)


@dp.message(Command("tvl"))
async def cmd_tvl(message: Message, command: CommandObject):
    if not await is_subscribed(message.from_user.id):
        await message.reply("❌ للمشتركين فقط")
        return
    wait = await message.reply("⏳ جاري جلب TVL...")
    protocol = command.args.strip() if command.args else None
    text = await get_tvl(protocol)
    await wait.edit_text(text)


@dp.message(Command("wyckoff"))
async def cmd_wyckoff(message: Message, command: CommandObject):
    if not await is_subscribed(message.from_user.id):
        await message.reply("❌ للمشتركين فقط")
        return
    symbol = (command.args or "BTC").strip().upper()
    wait = await message.reply(f"⏳ تحليل وايكوف لـ {symbol}...")
    klines = await get_binance_klines(symbol)
    if not klines:
        await wait.edit_text(f"❌ تعذر جلب بيانات {symbol} من Binance")
        return
    await wait.edit_text(simple_wyckoff(klines) + f"\n\nالرمز: <b>{symbol}</b>")


@dp.message(Command("elliott"))
async def cmd_elliott(message: Message, command: CommandObject):
    if not await is_subscribed(message.from_user.id):
        await message.reply("❌ للمشتركين فقط")
        return
    symbol = (command.args or "BTC").strip().upper()
    wait = await message.reply(f"⏳ تحليل إليوت لـ {symbol}...")
    klines = await get_binance_klines(symbol)
    if not klines:
        await wait.edit_text(f"❌ تعذر جلب بيانات {symbol}")
        return
    await wait.edit_text(simple_elliott(klines) + f"\n\nالرمز: <b>{symbol}</b>")


@dp.message(Command("harmonic"))
async def cmd_harmonic(message: Message, command: CommandObject):
    if not await is_subscribed(message.from_user.id):
        await message.reply("❌ للمشتركين فقط")
        return
    symbol = (command.args or "BTC").strip().upper()
    wait = await message.reply(f"⏳ الأنماط التوافقية لـ {symbol}...")
    klines = await get_binance_klines(symbol)
    if not klines:
        await wait.edit_text(f"❌ تعذر جلب بيانات {symbol}")
        return
    await wait.edit_text(simple_harmonic(klines) + f"\n\nالرمز: <b>{symbol}</b>")


@dp.message(Command("whales"))
async def cmd_whales(message: Message):
    if not await is_subscribed(message.from_user.id):
        await message.reply("❌ للمشتركين فقط")
        return
    text = (
        "<b>🐋 نشاط الحيتان</b>\n\n"
        "حالياً يتم عرض ملخص عام. للإشعارات الحية يُفضل ربط Whale Alert أو Arkham لاحقاً.\n\n"
        "• راقب التحويلات الكبيرة على Solana و Ethereum\n"
        "• الحيتان تتحرك غالباً قبل التقلبات الكبيرة\n"
        "• استخدم /market و /tvl مع التحليل الأساسي\n\n"
        "<i>نسخة قادمة: تنبيهات حيتان مباشرة.</i>"
    )
    await message.answer(text)


@dp.callback_query(F.data == "spot")
async def spot_menu(callback: CallbackQuery):
    if not await is_subscribed(callback.from_user.id):
        await callback.answer("❌ للمشتركين فقط", show_alert=True)
        return
    await callback.message.edit_text(
        "<b>📈 Spot</b>\n\n"
        "قسم الإشارات الفورية (Spot).\n"
        "قريباً: إشارات دخول/خروج + مستويات دعم ومقاومة.\n\n"
        "حالياً استخدم:\n"
        "• /analyze BTC\n"
        "• /wyckoff BTC\n"
        "• /market",
        reply_markup=back_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "futures")
async def futures_menu(callback: CallbackQuery):
    if not await is_subscribed(callback.from_user.id):
        await callback.answer("❌ للمشتركين فقط", show_alert=True)
        return
    await callback.message.edit_text(
        "<b>🚀 Futures</b>\n\n"
        "قسم العقود الآجلة.\n"
        "قريباً: إشارات برافعة + إدارة مخاطر + تصفية.\n\n"
        "استخدم التحليل الحالي ريثما يتم تفعيل الإشارات الحية.",
        reply_markup=back_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "favorites")
async def favorites_menu(callback: CallbackQuery):
    favs = await get_favorites(callback.from_user.id)
    text = "<b>⭐ عملاتك المفضلة</b>\n\n"
    if favs:
        text += "\n".join(f"• {s}" for s in favs)
    else:
        text += "لا توجد عملات مفضلة بعد."
    text += "\n\n<code>/add BTC</code> | <code>/remove BTC</code>"
    await callback.message.edit_text(text, reply_markup=back_kb())
    await callback.answer()


@dp.message(Command("add"))
async def add_cmd(message: Message, command: CommandObject):
    if not command.args:
        await message.reply("مثال: <code>/add BTC</code>")
        return
    ok = await add_favorite(message.from_user.id, command.args)
    await message.reply("✅ تمت الإضافة" if ok else "موجودة مسبقاً أو خطأ")


@dp.message(Command("remove"))
async def remove_cmd(message: Message, command: CommandObject):
    if not command.args:
        await message.reply("مثال: <code>/remove BTC</code>")
        return
    ok = await remove_favorite(message.from_user.id, command.args)
    await message.reply("✅ تم الحذف" if ok else "غير موجودة")


# ====================== نظام الدفع الحقيقي ======================
@dp.callback_query(F.data == "plans")
async def plans_menu(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="شهر — 20$", callback_data="buy_1m")],
        [InlineKeyboardButton(text="3 أشهر — 50$", callback_data="buy_3m")],
        [InlineKeyboardButton(text="6 أشهر — 75$", callback_data="buy_6m")],
        [InlineKeyboardButton(text="سنة — 125$", callback_data="buy_1y")],
        [InlineKeyboardButton(text="🔙", callback_data="back_main")]
    ])
    await callback.message.edit_text(
        "<b>💎 باقات VIP</b>\n\n"
        "بعد الدفع أرسل:\n"
        "<code>/verify الخطة الشبكة TX_HASH</code>\n"
        "مثال: <code>/verify 1m sol 5VERv8NMvzbJ...</code>",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("buy_"))
async def buy_plan(callback: CallbackQuery):
    plan = callback.data.split("_")[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◎ Solana (SOL)", callback_data=f"pay_{plan}_sol")],
        [InlineKeyboardButton(text="🟡 BNB", callback_data=f"pay_{plan}_bnb")],
        [InlineKeyboardButton(text="Ξ Ethereum (ETH)", callback_data=f"pay_{plan}_eth")],
        [InlineKeyboardButton(text="🔙", callback_data="plans")]
    ])
    await callback.message.edit_text(
        f"<b>{PLANS[plan]['name']}</b>\n"
        f"السعر: <b>{PLANS[plan]['price']}$</b>\n\n"
        f"اختر شبكة الدفع:",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("pay_"))
async def pay_info(callback: CallbackQuery):
    _, plan, network = callback.data.split("_")
    price_usd = PLANS[plan]["price"]

    # جلب السعر الحالي وعرض المبلغ التقريبي
    sym = {"sol": "SOL", "bnb": "BNB", "eth": "ETH"}[network]
    price = await get_crypto_price(network)
    approx = ""
    if price:
        amount = price_usd / price
        approx = f"\nالمبلغ التقريبي: <b>{amount:.6f} {sym}</b> (حسب السعر الحالي)"

    wallet = SOL_WALLET if network == "sol" else BNB_ETH_WALLET
    text = (
        f"<b>الدفع — {PLANS[plan]['name']}</b>\n"
        f"المبلغ المطلوب: <b>{price_usd}$</b>{approx}\n\n"
        f"أرسل المبلغ إلى:\n<code>{wallet}</code>\n\n"
        f"بعد التأكيد أرسل:\n"
        f"<code>/verify {plan} {network} TX_HASH</code>\n\n"
        f"⚠️ تأكد أن المعاملة مؤكدة قبل الإرسال."
    )
    await callback.message.edit_text(text, reply_markup=back_kb("plans"))
    await callback.answer()


@dp.message(Command("verify"))
async def verify_cmd(message: Message, command: CommandObject):
    if not command.args:
        await message.reply(
            "الصيغة:\n<code>/verify 1m sol TX_HASH</code>\n"
            "أو\n<code>/verify 3m bnb 0x...</code>"
        )
        return

    parts = command.args.split()
    if len(parts) < 3:
        await message.reply("الصيغة: /verify الخطة الشبكة TX_HASH")
        return

    plan, network, tx = parts[0].lower(), parts[1].lower(), parts[2]
    if plan not in PLANS:
        await message.reply("خطة غير صحيحة. استخدم: 1m / 3m / 6m / 1y")
        return
    if network not in ("sol", "bnb", "eth"):
        await message.reply("الشبكة يجب أن تكون: sol أو bnb أو eth")
        return

    if await is_hash_used(tx):
        await message.reply("❌ هذا الهاش مستخدم مسبقاً.")
        return

    wait = await message.reply("⏳ جاري التحقق الحقيقي من المعاملة على البلوكشين...")

    expected = PLANS[plan]["price"]
    if network == "sol":
        ok, msg, usd = await verify_solana_tx(tx, expected)
    else:
        ok, msg, usd = await verify_evm_tx(tx, network, expected)

    if not ok:
        await wait.edit_text(f"❌ فشل التحقق\n\n{msg}")
        return

    # تفعيل
    expire = await activate_sub(
        message.from_user.id, plan,
        message.from_user.username,
        message.from_user.full_name
    )
    await mark_hash(tx, message.from_user.id, plan, network, usd)

    await wait.edit_text(
        f"✅ <b>تم تفعيل الاشتراك بنجاح!</b>\n\n"
        f"{msg}\n"
        f"الباقة: <b>{PLANS[plan]['name']}</b>\n"
        f"ينتهي في: <b>{expire}</b>"
    )

    # إشعار الأدمن
    try:
        await bot.send_message(
            ADMIN_ID,
            f"💰 اشتراك جديد حقيقي\n"
            f"المستخدم: {message.from_user.id} (@{message.from_user.username})\n"
            f"الباقة: {plan}\n"
            f"الشبكة: {network}\n"
            f"المبلغ ≈ ${usd:.2f}\n"
            f"TX: <code>{tx}</code>"
        )
    except Exception:
        pass


# ====================== أدمن ======================
@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "<b>لوحة الأدمن</b>\n\n"
        "/give USER_ID 1m — إعطاء اشتراك\n"
        "/stats — إحصائيات سريعة"
    )


@dp.message(Command("give"))
async def give_cmd(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    try:
        uid_str, plan = command.args.split()
        uid = int(uid_str)
        if plan not in PLANS:
            await message.reply("خطة خاطئة")
            return
        expire = await activate_sub(uid, plan)
        await message.reply(f"✅ تم إعطاء <b>{plan}</b> لـ <code>{uid}</code>\nينتهي: {expire}")
        try:
            await bot.send_message(uid, f"🎁 تم تفعيل باقة <b>{PLANS[plan]['name']}</b> لك من الإدارة.\nينتهي: {expire}")
        except Exception:
            pass
    except Exception:
        await message.reply("الصيغة: /give 123456789 1m")


@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    try:
        if use_postgres:
            async with pool.acquire() as conn:
                total = await conn.fetchval("SELECT COUNT(*) FROM users")
                active = await conn.fetchval(
                    "SELECT COUNT(*) FROM users WHERE is_active=TRUE AND expire_date > NOW()"
                )
                payments = await conn.fetchval("SELECT COUNT(*) FROM used_hashes")
        else:
            import sqlite3
            conn = sqlite3.connect(SQLITE_PATH)
            total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM users WHERE is_active=1 AND expire_date > datetime('now')"
            ).fetchone()[0]
            payments = conn.execute("SELECT COUNT(*) FROM used_hashes").fetchone()[0]
            conn.close()
        await message.answer(
            f"<b>📊 إحصائيات</b>\n\n"
            f"إجمالي المستخدمين: <b>{total}</b>\n"
            f"الاشتراكات النشطة: <b>{active}</b>\n"
            f"المدفوعات المسجلة: <b>{payments}</b>"
        )
    except Exception as e:
        await message.answer(f"خطأ: {e}")


# ====================== التشغيل ======================
async def main():
    await init_db()
    logger.info("🚀 البوت يعمل الآن...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
