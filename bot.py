"""
Doshka Trading Pro
==================
بوت تحليل تداول + اشتراكات USDT تلقائية

الشبكات:
1) Ethereum ERC-20
2) BNB Smart Chain BEP-20
3) Solana SPL

الدفع:
- المستخدم لا يرسل Transaction Hash.
- البوت يراقب الشبكات تلقائياً.
- يتحقق من USDT + الشبكة + المبلغ + عنوان الاستقبال + التأكيد.
- يمنع استخدام نفس المعاملة مرتين.

مهم:
ضع BOT_TOKEN و ADMIN_ID في Environment Variables.
ويُفضّل وضع RPC URLs الخاصة بك للإنتاج.

المتطلبات:
pip install aiogram aiohttp matplotlib numpy

مثال Environment:
BOT_TOKEN=xxxxxxxx
ADMIN_ID=123456789

ETH_RPC_URL=https://cloudflare-eth.com
BSC_RPC_URL=https://bsc-dataseed.binance.org
SOL_RPC_URL=https://api.mainnet-beta.solana.com
"""

import asyncio
import os
import logging
import sqlite3
import io
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

import aiohttp

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
    BufferedInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# ============================================================
# الإعدادات
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

SQLITE_PATH = os.getenv(
    "SQLITE_PATH",
    "data/subscriptions.db"
)

# ============================================================
# المحافظ
# ============================================================

SOL_WALLET = (
    "5JSJzkF9GU6GA28J57xxBvSngoaHtbLGGwQkKHGUu1Dt"
)

ETH_WALLET = (
    "0xF79A1bEc46037dcA06077889F4bb1A111B67723e"
).lower()

BSC_WALLET = (
    "0xF79A1bEc46037dcA06077889F4bb1A111B67723e"
).lower()


# ============================================================
# RPC
# ============================================================

ETH_RPC_URL = os.getenv(
    "ETH_RPC_URL",
    "https://cloudflare-eth.com"
)

BSC_RPC_URL = os.getenv(
    "BSC_RPC_URL",
    "https://bsc-dataseed.binance.org"
)

SOL_RPC_URL = os.getenv(
    "SOL_RPC_URL",
    "https://api.mainnet-beta.solana.com"
)


# ============================================================
# USDT Contracts
# ============================================================

ETH_USDT_CONTRACT = (
    "0xdAC17F958D2ee523a2206206994597C13D831ec7"
).lower()

# BNB Smart Chain USDT representation commonly used on BSC.
# يمكن تغييره من Environment Variable.
BSC_USDT_CONTRACT = os.getenv(
    "BSC_USDT_CONTRACT",
    "0x55d398326f99059ff775485246999027B3197955"
).lower()

# Official Tether USDt mint on Solana.
SOL_USDT_MINT = (
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
)


# ============================================================
# Network configuration
# ============================================================

NETWORKS = {
    "eth": {
        "name": "Ethereum ERC-20",
        "wallet": ETH_WALLET,
        "rpc": ETH_RPC_URL,
        "usdt": ETH_USDT_CONTRACT,
        "decimals": 6,
        "confirmations": 12,
        "explorer": "https://etherscan.io/tx/",
    },
    "bsc": {
        "name": "BNB Smart Chain BEP-20",
        "wallet": BSC_WALLET,
        "rpc": BSC_RPC_URL,
        "usdt": BSC_USDT_CONTRACT,
        "decimals": 18,
        "confirmations": 15,
        "explorer": "https://bscscan.com/tx/",
    },
    "sol": {
        "name": "Solana SPL",
        "wallet": SOL_WALLET,
        "rpc": SOL_RPC_URL,
        "usdt": SOL_USDT_MINT,
        "decimals": 6,
        "confirmations": 1,
        "explorer": "https://solscan.io/tx/",
    },
}


# ============================================================
# إعدادات الدفع
# ============================================================

PAYMENT_SCAN_SECONDS = int(
    os.getenv("PAYMENT_SCAN_SECONDS", "15")
)

PAYMENT_TIMEOUT_MINUTES = int(
    os.getenv("PAYMENT_TIMEOUT_MINUTES", "30")
)

# عدد البلوكات التي يتم فحصها في كل طلب eth_getLogs
EVM_SCAN_CHUNK = int(
    os.getenv("EVM_SCAN_CHUNK", "500")
)

# موضوع ERC20 Transfer(address,address,uint256)
TRANSFER_TOPIC = (
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7"
    "f163c4a11628f55a9df523b3ef"
)


# ============================================================
# الخطط
# ============================================================

PLANS = {
    "1m": {
        "days": 30,
        "price": 20,
        "name": "شهر",
        "emoji": "📅",
    },
    "3m": {
        "days": 90,
        "price": 50,
        "name": "3 أشهر",
        "emoji": "💎",
    },
    "6m": {
        "days": 180,
        "price": 75,
        "name": "6 أشهر",
        "emoji": "👑",
    },
    "1y": {
        "days": 365,
        "price": 125,
        "name": "سنة",
        "emoji": "🏆",
    },
}


# ============================================================
# المدارس
# ============================================================

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


# ============================================================
# FSM
# ============================================================

class AnalysisStates(StatesGroup):
    waiting_for_custom_symbol = State()


# ============================================================
# Bot
# ============================================================

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN مطلوب")

if not ADMIN_ID:
    raise SystemExit("❌ ADMIN_ID مطلوب")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("doshka")


bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    ),
)

dp = Dispatcher(storage=MemoryStorage())


# ============================================================
# Database
# ============================================================

class Database:

    def __init__(self):
        self.sqlite_path = SQLITE_PATH

    def connect(self):
        conn = sqlite3.connect(
            self.sqlite_path,
            timeout=30,
        )
        conn.row_factory = sqlite3.Row
        return conn

    async def init(self):

        os.makedirs(
            os.path.dirname(self.sqlite_path) or ".",
            exist_ok=True,
        )

        conn = self.connect()

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                plan TEXT,
                start_date TEXT,
                expire_date TEXT,
                is_active INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan TEXT NOT NULL,
                network TEXT NOT NULL,
                expected_amount REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                tx_hash TEXT,
                sender TEXT,
                amount REAL,
                created_at TEXT NOT NULL,
                confirmed_at TEXT,
                error TEXT
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_tx_hash
            ON payments(tx_hash)
            WHERE tx_hash IS NOT NULL;

            CREATE TABLE IF NOT EXISTS used_transactions (
                tx_hash TEXT PRIMARY KEY,
                network TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                payment_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scanner_state (
                network TEXT PRIMARY KEY,
                last_block INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS solana_scanner_state (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                last_signature TEXT
            );
            """
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO users
            (user_id, username, is_active)
            VALUES (?, ?, 1)
            """,
            (
                ADMIN_ID,
                "admin",
            ),
        )

        conn.commit()
        conn.close()

        logger.info("✅ Database ready")

    async def update_username(
        self,
        uid: int,
        username: Optional[str],
    ):
        conn = self.connect()

        conn.execute(
            """
            INSERT INTO users
            (user_id, username, is_active)
            VALUES (?, ?, 0)
            ON CONFLICT(user_id)
            DO UPDATE SET username=excluded.username
            """,
            (
                uid,
                username or "",
            ),
        )

        conn.commit()
        conn.close()

    async def is_subscribed(
        self,
        uid: int,
    ) -> bool:

        if uid == ADMIN_ID:
            return True

        conn = self.connect()

        row = conn.execute(
            """
            SELECT expire_date
            FROM users
            WHERE user_id=?
            AND is_active=1
            """,
            (uid,),
        ).fetchone()

        conn.close()

        if not row:
            return False

        if not row["expire_date"]:
            return False

        try:
            expire = datetime.fromisoformat(
                row["expire_date"]
            )

            if expire <= datetime.now():
                conn = self.connect()

                conn.execute(
                    """
                    UPDATE users
                    SET is_active=0
                    WHERE user_id=?
                    """,
                    (uid,),
                )

                conn.commit()
                conn.close()

                return False

            return True

        except Exception:
            return False

    async def get_user_subscription(
        self,
        uid: int,
    ) -> Optional[Dict]:

        conn = self.connect()

        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE user_id=?
            """,
            (uid,),
        ).fetchone()

        conn.close()

        return dict(row) if row else None

    async def activate_subscription(
        self,
        uid: int,
        plan_id: str,
    ) -> str:

        now = datetime.now()

        conn = self.connect()

        row = conn.execute(
            """
            SELECT expire_date
            FROM users
            WHERE user_id=?
            """,
            (uid,),
        ).fetchone()

        base = now

        if row and row["expire_date"]:
            try:
                old_expire = datetime.fromisoformat(
                    row["expire_date"]
                )

                if old_expire > now:
                    base = old_expire

            except Exception:
                pass

        expire = base + timedelta(
            days=PLANS[plan_id]["days"]
        )

        conn.execute(
            """
            INSERT INTO users
            (
                user_id,
                plan,
                start_date,
                expire_date,
                is_active
            )
            VALUES (?, ?, ?, ?, 1)

            ON CONFLICT(user_id)
            DO UPDATE SET
                plan=excluded.plan,
                start_date=excluded.start_date,
                expire_date=excluded.expire_date,
                is_active=1
            """,
            (
                uid,
                plan_id,
                now.isoformat(),
                expire.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        return expire.strftime(
            "%Y-%m-%d %H:%M"
        )

    async def create_payment(
        self,
        uid: int,
        plan_id: str,
        network: str,
    ) -> int:

        conn = self.connect()

        cur = conn.execute(
            """
            INSERT INTO payments
            (
                user_id,
                plan,
                network,
                expected_amount,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (
                uid,
                plan_id,
                network,
                float(PLANS[plan_id]["price"]),
                datetime.now().isoformat(),
            ),
        )

        payment_id = cur.lastrowid

        conn.commit()
        conn.close()

        return int(payment_id)

    async def get_pending_payments(
        self,
        network: Optional[str] = None,
    ) -> List[Dict]:

        conn = self.connect()

        if network:
            rows = conn.execute(
                """
                SELECT *
                FROM payments
                WHERE status='pending'
                AND network=?
                ORDER BY id ASC
                """,
                (network,),
            ).fetchall()

        else:
            rows = conn.execute(
                """
                SELECT *
                FROM payments
                WHERE status='pending'
                ORDER BY id ASC
                """
            ).fetchall()

        conn.close()

        return [dict(r) for r in rows]

    async def get_payment(
        self,
        payment_id: int,
    ) -> Optional[Dict]:

        conn = self.connect()

        row = conn.execute(
            """
            SELECT *
            FROM payments
            WHERE id=?
            """,
            (payment_id,),
        ).fetchone()

        conn.close()

        return dict(row) if row else None

    async def mark_payment_paid(
        self,
        payment_id: int,
        tx_hash: str,
        sender: str,
        amount: float,
    ) -> bool:

        conn = self.connect()

        try:

            existing = conn.execute(
                """
                SELECT id
                FROM used_transactions
                WHERE tx_hash=?
                """,
                (
                    tx_hash.lower(),
                ),
            ).fetchone()

            if existing:
                conn.rollback()
                conn.close()
                return False

            payment = conn.execute(
                """
                SELECT *
                FROM payments
                WHERE id=?
                """,
                (
                    payment_id,
                ),
            ).fetchone()

            if not payment:
                conn.rollback()
                conn.close()
                return False

            if payment["status"] != "pending":
                conn.rollback()
                conn.close()
                return False

            now = datetime.now().isoformat()

            conn.execute(
                """
                UPDATE payments
                SET
                    status='paid',
                    tx_hash=?,
                    sender=?,
                    amount=?,
                    confirmed_at=?
                WHERE id=?
                AND status='pending'
                """,
                (
                    tx_hash.lower(),
                    sender,
                    amount,
                    now,
                    payment_id,
                ),
            )

            conn.execute(
                """
                INSERT INTO used_transactions
                (
                    tx_hash,
                    network,
                    user_id,
                    payment_id,
                    amount,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tx_hash.lower(),
                    payment["network"],
                    payment["user_id"],
                    payment_id,
                    amount,
                    now,
                ),
            )

            conn.commit()
            conn.close()

            return True

        except sqlite3.IntegrityError:

            conn.rollback()
            conn.close()

            return False

        except Exception:

            conn.rollback()
            conn.close()

            logger.exception(
                "mark_payment_paid error"
            )

            return False

    async def mark_payment_error(
        self,
        payment_id: int,
        error: str,
    ):

        conn = self.connect()

        conn.execute(
            """
            UPDATE payments
            SET error=?
            WHERE id=?
            AND status='pending'
            """,
            (
                error[:1000],
                payment_id,
            ),
        )

        conn.commit()
        conn.close()

    async def expire_old_payments(self):

        cutoff = datetime.now() - timedelta(
            minutes=PAYMENT_TIMEOUT_MINUTES
        )

        conn = self.connect()

        conn.execute(
            """
            UPDATE payments
            SET status='expired'
            WHERE status='pending'
            AND created_at < ?
            """,
            (
                cutoff.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

    async def get_scanner_block(
        self,
        network: str,
    ) -> int:

        conn = self.connect()

        row = conn.execute(
            """
            SELECT last_block
            FROM scanner_state
            WHERE network=?
            """,
            (
                network,
            ),
        ).fetchone()

        conn.close()

        return int(row["last_block"]) if row else 0

    async def set_scanner_block(
        self,
        network: str,
        block: int,
    ):

        conn = self.connect()

        conn.execute(
            """
            INSERT INTO scanner_state
            (network, last_block)
            VALUES (?, ?)
            ON CONFLICT(network)
            DO UPDATE SET
                last_block=excluded.last_block
            """,
            (
                network,
                block,
            ),
        )

        conn.commit()
        conn.close()

    async def get_solana_signature(
        self,
    ) -> Optional[str]:

        conn = self.connect()

        row = conn.execute(
            """
            SELECT last_signature
            FROM solana_scanner_state
            WHERE id=1
            """
        ).fetchone()

        conn.close()

        return row["last_signature"] if row else None

    async def set_solana_signature(
        self,
        signature: str,
    ):

        conn = self.connect()

        conn.execute(
            """
            INSERT INTO solana_scanner_state
            (id, last_signature)
            VALUES (1, ?)
            ON CONFLICT(id)
            DO UPDATE SET
                last_signature=excluded.last_signature
            """,
            (
                signature,
            ),
        )

        conn.commit()
        conn.close()


db = Database()


# ============================================================
# HTTP RPC helpers
# ============================================================

async def rpc_request(
    session: aiohttp.ClientSession,
    url: str,
    method: str,
    params: list,
) -> Any:

    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000) % 1000000000,
        "method": method,
        "params": params,
    }

    async with session.post(
        url,
        json=payload,
        timeout=aiohttp.ClientTimeout(
            total=20
        ),
    ) as resp:

        if resp.status != 200:
            raise RuntimeError(
                f"RPC HTTP {resp.status}"
            )

        data = await resp.json()

    if data.get("error"):
        raise RuntimeError(
            str(data["error"])
        )

    return data.get("result")


# ============================================================
# EVM helpers
# ============================================================

def hex_to_int(
    value: Optional[str],
) -> int:

    if not value:
        return 0

    return int(value, 16)


def pad_address_topic(
    address: str,
) -> str:

    return (
        "0x"
        + "0" * 24
        + address.lower().replace("0x", "")
    )


def topic_to_address(
    topic: str,
) -> str:

    return (
        "0x"
        + topic[-40:]
    ).lower()


def amount_from_raw(
    raw: int,
    decimals: int,
) -> float:

    return raw / (10 ** decimals)


async def get_latest_evm_block(
    session,
    network: str,
) -> int:

    cfg = NETWORKS[network]

    result = await rpc_request(
        session,
        cfg["rpc"],
        "eth_blockNumber",
        [],
    )

    return hex_to_int(result)


async def get_evm_logs(
    session,
    network: str,
    from_block: int,
    to_block: int,
) -> List[Dict]:

    cfg = NETWORKS[network]

    result = await rpc_request(
        session,
        cfg["rpc"],
        "eth_getLogs",
        [
            {
                "fromBlock": hex(from_block),
                "toBlock": hex(to_block),
                "address": cfg["usdt"],
                "topics": [
                    TRANSFER_TOPIC,
                    None,
                    pad_address_topic(
                        cfg["wallet"]
                    ),
                ],
            }
        ],
    )

    return result or []


async def get_evm_block_timestamp(
    session,
    network: str,
    block_number: int,
) -> int:

    cfg = NETWORKS[network]

    result = await rpc_request(
        session,
        cfg["rpc"],
        "eth_getBlockByNumber",
        [
            hex(block_number),
            False,
        ],
    )

    if not result:
        return 0

    return hex_to_int(
        result.get("timestamp")
    )


async def verify_evm_log(
    session,
    network: str,
    log: Dict,
) -> Optional[Dict]:

    cfg = NETWORKS[network]

    try:

        address = (
            log.get("address", "")
            .lower()
        )

        if address != cfg["usdt"]:
            return None

        topics = log.get(
            "topics",
            [],
        )

        if len(topics) < 3:
            return None

        sender = topic_to_address(
            topics[1]
        )

        recipient = topic_to_address(
            topics[2]
        )

        if recipient != cfg["wallet"].lower():
            return None

        raw_amount = hex_to_int(
            log.get("data")
        )

        amount = amount_from_raw(
            raw_amount,
            cfg["decimals"],
        )

        block_number = hex_to_int(
            log.get("blockNumber")
        )

        latest_block = await get_latest_evm_block(
            session,
            network,
        )

        confirmations = (
            latest_block
            - block_number
            + 1
        )

        if confirmations < cfg["confirmations"]:
            return None

        tx_hash = log.get(
            "transactionHash"
        )

        if not tx_hash:
            return None

        return {
            "network": network,
            "tx_hash": tx_hash.lower(),
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "block": block_number,
            "confirmations": confirmations,
        }

    except Exception:

        logger.exception(
            "verify_evm_log error"
        )

        return None


# ============================================================
# Solana helpers
# ============================================================

async def get_sol_usdt_token_accounts(
    session,
) -> List[str]:

    result = await rpc_request(
        session,
        SOL_RPC_URL,
        "getTokenAccountsByOwner",
        [
            SOL_WALLET,
            {
                "mint": SOL_USDT_MINT,
            },
            {
                "commitment": "finalized",
                "encoding": "jsonParsed",
            },
        ],
    )

    accounts = []

    for item in (result or {}).get(
        "value",
        [],
    ):

        pubkey = item.get(
            "pubkey"
        )

        if pubkey:
            accounts.append(pubkey)

    return accounts


async def get_sol_signatures(
    session,
    token_account: str,
    limit: int = 20,
) -> List[Dict]:

    result = await rpc_request(
        session,
        SOL_RPC_URL,
        "getSignaturesForAddress",
        [
            token_account,
            {
                "limit": limit,
                "commitment": "finalized",
            },
        ],
    )

    return result or []


def extract_sol_transfer_amount(
    tx: Dict,
    token_account: str,
) -> float:

    meta = tx.get(
        "meta"
    ) or {}

    if meta.get("err") is not None:
        return 0.0

    pre = meta.get(
        "preTokenBalances",
        [],
    )

    post = meta.get(
        "postTokenBalances",
        [],
    )

    pre_amount = 0
    post_amount = 0
    decimals = 6

    for item in pre:

        if item.get(
            "mint"
        ) != SOL_USDT_MINT:
            continue

        owner = item.get(
            "owner"
        )

        account_index = item.get(
            "accountIndex"
        )

        try:
            parsed = item.get(
                "uiTokenAmount",
                {},
            )

            decimals = int(
                parsed.get(
                    "decimals",
                    6,
                )
            )

            raw = int(
                parsed.get(
                    "amount",
                    "0",
                )
            )

            pre_amount += raw

        except Exception:
            pass

    for item in post:

        if item.get(
            "mint"
        ) != SOL_USDT_MINT:
            continue

        try:
            parsed = item.get(
                "uiTokenAmount",
                {},
            )

            decimals = int(
                parsed.get(
                    "decimals",
                    6,
                )
            )

            raw = int(
                parsed.get(
                    "amount",
                    "0",
                )
            )

            post_amount += raw

        except Exception:
            pass

    delta = post_amount - pre_amount

    if delta <= 0:
        return 0.0

    return amount_from_raw(
        delta,
        decimals,
    )


async def verify_sol_transaction(
    session,
    signature: str,
    token_account: str,
) -> Optional[Dict]:

    try:

        tx = await rpc_request(
            session,
            SOL_RPC_URL,
            "getTransaction",
            [
                signature,
                {
                    "commitment": "finalized",
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0,
                },
            ],
        )

        if not tx:
            return None

        meta = tx.get(
            "meta"
        ) or {}

        if meta.get("err") is not None:
            return None

        amount = extract_sol_transfer_amount(
            tx,
            token_account,
        )

        if amount <= 0:
            return None

        sender = ""

        try:

            message = (
                tx.get("transaction", {})
                .get("message", {})
            )

            account_keys = message.get(
                "accountKeys",
                [],
            )

            if account_keys:
                first = account_keys[0]

                if isinstance(
                    first,
                    dict,
                ):
                    sender = first.get(
                        "pubkey",
                        "",
                    )

                else:
                    sender = str(first)

        except Exception:
            sender = ""

        return {
            "network": "sol",
            "tx_hash": signature,
            "sender": sender,
            "recipient": SOL_WALLET,
            "amount": amount,
            "confirmations": 1,
        }

    except Exception:

        logger.exception(
            "verify_sol_transaction error"
        )

        return None


# ============================================================
# Payment matching
# ============================================================

def payment_matches(
    payment: Dict,
    transfer: Dict,
) -> bool:

    expected = float(
        payment["expected_amount"]
    )

    received = float(
        transfer["amount"]
    )

    # لا نقبل أقل من المطلوب.
    # نسمح بفارق صغير جداً بسبب تمثيل الأرقام.
    if received + 1e-9 < expected:
        return False

    # يجب أن تكون الشبكة نفسها.
    if payment["network"] != transfer["network"]:
        return False

    return True


async def process_detected_transfer(
    transfer: Dict,
):

    network = transfer["network"]

    pending = await db.get_pending_payments(
        network
    )

    if not pending:
        return

    candidates = []

    transfer_time = datetime.now()

    for payment in pending:

        try:

            created = datetime.fromisoformat(
                payment["created_at"]
            )

        except Exception:
            continue

        # لا نربط تحويلات قديمة جداً بجلسة جديدة.
        if created > transfer_time:
            continue

        if (
            transfer_time - created
        ).total_seconds() > (
            PAYMENT_TIMEOUT_MINUTES * 60
        ):
            continue

        if payment_matches(
            payment,
            transfer,
        ):
            candidates.append(
                payment
            )

    if not candidates:
        return

    # ========================================================
    # حماية مهمة:
    # إذا كان أكثر من مستخدم ينتظر نفس المبلغ
    # في نفس الشبكة، لا نربط الدفع عشوائياً.
    # ========================================================

    if len(candidates) > 1:

        logger.warning(
            "Ambiguous payment: %s candidates, network=%s amount=%s tx=%s",
            len(candidates),
            network,
            transfer["amount"],
            transfer["tx_hash"],
        )

        try:
            await bot.send_message(
                ADMIN_ID,
                (
                    "⚠️ <b>دفعة تحتاج مراجعة يدوية</b>\n\n"
                    f"الشبكة: <b>{network}</b>\n"
                    f"المبلغ: <b>{transfer['amount']:.6f} USDT</b>\n"
                    f"TX: <code>{transfer['tx_hash']}</code>\n"
                    f"عدد جلسات الدفع المتطابقة: <b>{len(candidates)}</b>\n\n"
                    "لم يتم تفعيل أي حساب تلقائياً لتجنب ربط الدفع بالمستخدم الخطأ."
                ),
            )

        except Exception:
            pass

        return

    payment = candidates[0]

    success = await db.mark_payment_paid(
        payment["id"],
        transfer["tx_hash"],
        transfer.get("sender", ""),
        transfer["amount"],
    )

    if not success:
        return

    expire = await db.activate_subscription(
        payment["user_id"],
        payment["plan"],
    )

    try:

        plan = PLANS[
            payment["plan"]
        ]

        network_name = NETWORKS[
            network
        ]["name"]

        explorer = NETWORKS[
            network
        ]["explorer"]

        await bot.send_message(
            payment["user_id"],
            (
                "🎉 <b>تم تأكيد الدفع وتفعيل الاشتراك!</b>\n\n"
                f"📦 الباقة: <b>{plan['name']}</b>\n"
                f"💰 المدفوع: <b>{transfer['amount']:.6f} USDT</b>\n"
                f"🌐 الشبكة: <b>{network_name}</b>\n"
                f"📅 ينتهي: <b>{expire}</b>\n\n"
                f"🔗 <a href=\"{explorer}{transfer['tx_hash']}\">عرض المعاملة</a>\n\n"
                "يمكنك الآن استخدام جميع أدوات التحليل."
            ),
        )

    except Exception:

        logger.exception(
            "Failed to notify user"
        )

    try:

        await bot.send_message(
            ADMIN_ID,
            (
                "💰 <b>تم استلام دفعة USDT</b>\n\n"
                f"👤 المستخدم: <code>{payment['user_id']}</code>\n"
                f"📦 الباقة: <b>{PLANS[payment['plan']]['name']}</b>\n"
                f"💵 المبلغ: <b>{transfer['amount']:.6f} USDT</b>\n"
                f"🌐 الشبكة: <b>{network_name}</b>\n"
                f"TX: <code>{transfer['tx_hash']}</code>\n"
                f"📅 الانتهاء: <b>{expire}</b>"
            ),
        )

    except Exception:
        pass


# ============================================================
# EVM scanner
# ============================================================

async def scan_evm_network(
    session,
    network: str,
):

    cfg = NETWORKS[network]

    latest = await get_latest_evm_block(
        session,
        network,
    )

    last = await db.get_scanner_block(
        network
    )

    # أول تشغيل:
    # نبدأ من آخر 100 بلوك تقريباً حتى لا نقرأ
    # تاريخ الشبكة بالكامل.
    if last <= 0:

        last = max(
            0,
            latest - 100,
        )

    if last >= latest:
        return

    current = last + 1

    while current <= latest:

        end = min(
            current + EVM_SCAN_CHUNK - 1,
            latest,
        )

        try:

            logs = await get_evm_logs(
                session,
                network,
                current,
                end,
            )

            for log in logs:

                transfer = await verify_evm_log(
                    session,
                    network,
                    log,
                )

                if transfer:

                    await process_detected_transfer(
                        transfer
                    )

            await db.set_scanner_block(
                network,
                end,
            )

            current = end + 1

        except Exception as e:

            logger.error(
                "EVM scanner %s error: %s",
                network,
                e,
            )

            # لا نضع last block على latest
            # إذا فشل RPC.
            break


# ============================================================
# Solana scanner
# ============================================================

async def scan_solana(
    session,
):

    try:

        token_accounts = (
            await get_sol_usdt_token_accounts(
                session
            )
        )

        if not token_accounts:
            logger.warning(
                "No Solana USDT token account found."
            )
            return

        # نفحص الحسابات التابعة لمحفظتنا.
        for token_account in token_accounts:

            signatures = (
                await get_sol_signatures(
                    session,
                    token_account,
                    20,
                )
            )

            for item in signatures:

                signature = item.get(
                    "signature"
                )

                if not signature:
                    continue

                if item.get("err") is not None:
                    continue

                transfer = (
                    await verify_sol_transaction(
                        session,
                        signature,
                        token_account,
                    )
                )

                if transfer:

                    await process_detected_transfer(
                        transfer
                    )

    except Exception:

        logger.exception(
            "Solana scanner error"
        )


# ============================================================
# Payment monitor
# ============================================================

async def payment_monitor():

    logger.info(
        "💰 Payment monitor started"
    )

    timeout = aiohttp.ClientTimeout(
        total=30
    )

    connector = aiohttp.TCPConnector(
        limit=20,
        ssl=True,
    )

    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
    ) as session:

        while True:

            try:

                await db.expire_old_payments()

                await asyncio.gather(
                    scan_evm_network(
                        session,
                        "eth",
                    ),
                    scan_evm_network(
                        session,
                        "bsc",
                    ),
                    scan_solana(
                        session
                    ),
                    return_exceptions=True,
                )

            except Exception:

                logger.exception(
                    "Payment monitor main loop error"
                )

            await asyncio.sleep(
                PAYMENT_SCAN_SECONDS
            )


# ============================================================
# Binance market data
# ============================================================

async def get_klines(
    symbol: str,
    interval: str = "4h",
    limit: int = 100,
) -> List[Dict]:

    symbol = (
        symbol.upper()
        .replace("/", "")
        .replace("USDT", "")
        .strip()
    )

    url = (
        "https://api.binance.com/api/v3/klines"
        f"?symbol={symbol}USDT"
        f"&interval={interval}"
        f"&limit={limit}"
    )

    try:

        timeout = aiohttp.ClientTimeout(
            total=15
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(
                url
            ) as resp:

                if resp.status != 200:
                    return []

                data = await resp.json()

        result = []

        for k in data:

            result.append(
                {
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "time": datetime.fromtimestamp(
                        k[0] / 1000
                    ),
                }
            )

        return result

    except Exception as e:

        logger.error(
            "Binance error: %s",
            e,
        )

        return []


# ============================================================
# Indicators
# ============================================================

def calculate_rsi(
    closes: List[float],
    period: int = 14,
) -> float:

    if len(closes) < period + 1:
        return 50.0

    gains = []
    losses = []

    for i in range(1, len(closes)):

        change = (
            closes[i] - closes[i - 1]
        )

        gains.append(
            max(0, change)
        )

        losses.append(
            max(0, -change)
        )

    avg_gain = (
        sum(gains[-period:]) / period
    )

    avg_loss = (
        sum(losses[-period:]) / period
    )

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss

    return 100 - (
        100 / (1 + rs)
    )


def calculate_ema(
    values: List[float],
    period: int,
) -> List[float]:

    if not values:
        return []

    ema = [values[0]]

    multiplier = (
        2 / (period + 1)
    )

    for i in range(1, len(values)):

        ema.append(
            (
                values[i] - ema[-1]
            ) * multiplier
            + ema[-1]
        )

    return ema


def calculate_macd(
    closes: List[float],
) -> Dict[str, float]:

    if len(closes) < 26:
        return {
            "macd": 0,
            "signal": 0,
            "histogram": 0,
        }

    ema12 = calculate_ema(
        closes,
        12,
    )

    ema26 = calculate_ema(
        closes,
        26,
    )

    macd_line = [
        ema12[i] - ema26[i]
        for i in range(len(closes))
    ]

    signal_line = calculate_ema(
        macd_line,
        9,
    )

    return {
        "macd": macd_line[-1],
        "signal": signal_line[-1],
        "histogram": (
            macd_line[-1]
            - signal_line[-1]
        ),
    }


def find_sr(
    klines: List[Dict],
) -> Dict:

    if len(klines) < 7:

        current = (
            klines[-1]["close"]
            if klines
            else 0
        )

        return {
            "supports": [],
            "resistances": [],
        }

    highs = [
        k["high"]
        for k in klines
    ]

    lows = [
        k["low"]
        for k in klines
    ]

    levels = []

    for i in range(
        2,
        len(highs) - 2,
    ):

        if (
            highs[i] > highs[i - 1]
            and highs[i] > highs[i + 1]
        ):
            levels.append(
                highs[i]
            )

        if (
            lows[i] < lows[i - 1]
            and lows[i] < lows[i + 1]
        ):
            levels.append(
                lows[i]
            )

    current = klines[-1]["close"]

    supports = sorted(
        [
            x
            for x in levels
            if x < current
        ],
        reverse=True,
    )[:3]

    resistances = sorted(
        [
            x
            for x in levels
            if x > current
        ]
    )[:3]

    return {
        "supports": supports,
        "resistances": resistances,
    }


# ============================================================
# Trading analyses
# ============================================================

def trade_levels(
    klines: List[Dict],
    action: str,
    tp1: float,
    tp2: float,
    sl_mult: float = 0.97,
):

    current = klines[-1]["close"]

    sr = find_sr(
        klines
    )

    if action == "BUY":

        entry = [round(current, 4)]

        if sr["supports"]:
            entry.append(
                round(
                    sr["supports"][0],
                    4,
                )
            )

        stop_loss = round(
            min(
                k["low"]
                for k in klines[-20:]
            )
            * sl_mult,
            4,
        )

        take_profit = [
            round(
                current * tp1,
                4,
            ),
            round(
                current * tp2,
                4,
            ),
        ]

    elif action == "SELL":

        entry = [round(current, 4)]

        if sr["resistances"]:
            entry.append(
                round(
                    sr["resistances"][0],
                    4,
                )
            )

        stop_loss = round(
            max(
                k["high"]
                for k in klines[-20:]
            )
            * (2 - sl_mult),
            4,
        )

        take_profit = [
            round(
                current * (2 - tp1),
                4,
            ),
            round(
                current * (2 - tp2),
                4,
            ),
        ]

    else:

        entry = [
            round(
                current,
                4,
            )
        ]

        stop_loss = round(
            current * 0.95,
            4,
        )

        take_profit = [
            round(
                current * 1.05,
                4,
            )
        ]

    return (
        entry,
        stop_loss,
        take_profit,
        sr,
    )


def action_text(
    action: str,
) -> str:

    return {
        "BUY": "🟢 شراء",
        "SELL": "🔴 بيع",
        "WAIT": "⏳ انتظار",
    }.get(
        action,
        "⏳ انتظار",
    )


def wyckoff_analysis(
    klines,
    symbol,
):

    closes = [
        k["close"]
        for k in klines
    ]

    volumes = [
        k["volume"]
        for k in klines
    ]

    current = closes[-1]

    avg_vol = (
        sum(volumes[:-10])
        / max(
            len(volumes[:-10]),
            1,
        )
    )

    recent_vol = (
        sum(volumes[-10:]) / 10
    )

    vol_ratio = (
        recent_vol / avg_vol
        if avg_vol
        else 1
    )

    rsi = calculate_rsi(
        closes
    )

    action = "WAIT"
    confidence = 50
    phase = "تجميع/انتظار"

    if (
        vol_ratio > 1.5
        and rsi < 40
    ):

        action = "BUY"
        confidence = 80
        phase = "مرحلة التجميع"

    elif (
        vol_ratio > 1.5
        and rsi > 60
    ):

        action = "SELL"
        confidence = 80
        phase = "مرحلة التوزيع"

    elif (
        vol_ratio > 1.2
        and rsi < 50
    ):

        action = "BUY"
        confidence = 70
        phase = "بداية تجميع"

    elif (
        vol_ratio > 1.2
        and rsi > 50
    ):

        action = "SELL"
        confidence = 70
        phase = "بداية توزيع"

    entry, sl, tp, sr = trade_levels(
        klines,
        action,
        1.03,
        1.06,
    )

    analysis = (
        f"📊 <b>تحليل وايكوف - {symbol}/USDT</b>\n\n"
        f"المرحلة: <b>{phase}</b>\n"
        f"نسبة الحجم: <b>{vol_ratio:.2f}x</b>\n"
        f"RSI: <b>{rsi:.1f}</b>\n\n"
        f"التوصية: <b>{action_text(action)}</b>\n"
        f"الثقة: <b>{confidence}%</b>\n\n"
        f"💡 الدخول: {', '.join(f'${x}' for x in entry)}\n"
        f"🛑 الوقف: ${sl}\n"
        f"🎯 الأهداف: {', '.join(f'${x}' for x in tp)}"
    )

    return {
        "analysis": analysis,
        "action": action,
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "sr": sr,
        "rsi": rsi,
    }


def elliott_analysis(
    klines,
    symbol,
):

    closes = [
        k["close"]
        for k in klines
    ]

    highs = [
        k["high"]
        for k in klines
    ]

    lows = [
        k["low"]
        for k in klines
    ]

    pivots = []

    for i in range(
        3,
        len(klines) - 3,
    ):

        if (
            highs[i] > highs[i - 1]
            and highs[i] > highs[i - 2]
            and highs[i] > highs[i + 1]
            and highs[i] > highs[i + 2]
        ):

            pivots.append(
                {
                    "type": "H",
                    "price": highs[i],
                }
            )

        elif (
            lows[i] < lows[i - 1]
            and lows[i] < lows[i - 2]
            and lows[i] < lows[i + 1]
            and lows[i] < lows[i + 2]
        ):

            pivots.append(
                {
                    "type": "L",
                    "price": lows[i],
                }
            )

    action = "WAIT"
    confidence = 50
    wave = "موجة غير محددة"

    if len(pivots) >= 3:

        last = pivots[-1]

        if last["type"] == "L":

            action = "BUY"
            confidence = 70
            wave = "احتمال نهاية تصحيح وبداية موجة صاعدة"

        elif last["type"] == "H":

            action = "SELL"
            confidence = 70
            wave = "احتمال نهاية موجة صاعدة وبداية تصحيح"

    entry, sl, tp, sr = trade_levels(
        klines,
        action,
        1.05,
        1.08,
    )

    rsi = calculate_rsi(
        closes
    )

    analysis = (
        f"🌊 <b>تحليل إليوت - {symbol}/USDT</b>\n\n"
        f"الموجة: <b>{wave}</b>\n"
        f"النقاط المحورية: <b>{len(pivots)}</b>\n"
        f"RSI: <b>{rsi:.1f}</b>\n\n"
        f"التوصية: <b>{action_text(action)}</b>\n"
        f"الثقة: <b>{confidence}%</b>\n\n"
        f"💡 الدخول: {', '.join(f'${x}' for x in entry)}\n"
        f"🛑 الوقف: ${sl}\n"
        f"🎯 الأهداف: {', '.join(f'${x}' for x in tp)}"
    )

    return {
        "analysis": analysis,
        "action": action,
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "sr": sr,
        "rsi": rsi,
    }


def harmonic_analysis(
    klines,
    symbol,
):

    closes = [
        k["close"]
        for k in klines
    ]

    highs = [
        k["high"]
        for k in klines
    ]

    lows = [
        k["low"]
        for k in klines
    ]

    recent_high = max(
        highs[-25:]
    )

    recent_low = min(
        lows[-25:]
    )

    current = closes[-1]

    price_range = (
        recent_high - recent_low
    )

    retracement = (
        (
            recent_high - current
        )
        / price_range
        if price_range
        else 0.5
    )

    action = "WAIT"
    confidence = 50
    pattern = "لا يوجد نمط واضح"

    if 0.55 <= retracement <= 0.65:

        pattern = "Gartley"
        action = "BUY"
        confidence = 75

    elif 0.70 <= retracement <= 0.80:

        pattern = "Butterfly"
        action = "BUY"
        confidence = 80

    elif 0.35 <= retracement <= 0.50:

        pattern = "Bat"
        action = "BUY"
        confidence = 70

    elif 0.80 <= retracement <= 0.90:

        pattern = "Crab"
        action = "SELL"
        confidence = 75

    entry, sl, tp, sr = trade_levels(
        klines,
        action,
        1.05,
        1.10,
    )

    rsi = calculate_rsi(
        closes
    )

    analysis = (
        f"🦋 <b>تحليل هارمونيك - {symbol}/USDT</b>\n\n"
        f"النمط: <b>{pattern}</b>\n"
        f"التصحيح: <b>{retracement * 100:.1f}%</b>\n"
        f"RSI: <b>{rsi:.1f}</b>\n\n"
        f"التوصية: <b>{action_text(action)}</b>\n"
        f"الثقة: <b>{confidence}%</b>\n\n"
        f"💡 الدخول: {', '.join(f'${x}' for x in entry)}\n"
        f"🛑 الوقف: ${sl}\n"
        f"🎯 الأهداف: {', '.join(f'${x}' for x in tp)}"
    )

    return {
        "analysis": analysis,
        "action": action,
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "sr": sr,
        "rsi": rsi,
    }


def classic_analysis(
    klines,
    symbol,
):

    closes = [
        k["close"]
        for k in klines
    ]

    current = closes[-1]

    rsi = calculate_rsi(
        closes
    )

    macd = calculate_macd(
        closes
    )

    signals = []

    if rsi < 30:

        action = "BUY"
        confidence = 80
        signals.append(
            "RSI تشبع بيعي"
        )

    elif rsi > 70:

        action = "SELL"
        confidence = 80
        signals.append(
            "RSI تشبع شرائي"
        )

    elif macd["histogram"] > 0:

        action = "BUY"
        confidence = 65
        signals.append(
            "MACD إيجابي"
        )

    elif macd["histogram"] < 0:

        action = "SELL"
        confidence = 65
        signals.append(
            "MACD سلبي"
        )

    else:

        action = "WAIT"
        confidence = 50

    entry, sl, tp, sr = trade_levels(
        klines,
        action,
        1.04,
        1.08,
    )

    analysis = (
        f"📈 <b>تحليل كلاسيكي - {symbol}/USDT</b>\n\n"
        f"RSI: <b>{rsi:.1f}</b>\n"
        f"MACD: <b>{'إيجابي' if macd['histogram'] > 0 else 'سلبي'}</b>\n"
        f"الإشارات: {', '.join(signals) if signals else 'لا توجد'}\n\n"
        f"التوصية: <b>{action_text(action)}</b>\n"
        f"الثقة: <b>{confidence}%</b>\n\n"
        f"💡 الدخول: {', '.join(f'${x}' for x in entry)}\n"
        f"🛑 الوقف: ${sl}\n"
        f"🎯 الأهداف: {', '.join(f'${x}' for x in tp)}"
    )

    return {
        "analysis": analysis,
        "action": action,
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "sr": sr,
        "rsi": rsi,
        "macd": macd,
    }


def whales_analysis(
    klines,
    symbol,
):

    closes = [
        k["close"]
        for k in klines
    ]

    volumes = [
        k["volume"]
        for k in klines
    ]

    avg_vol = (
        sum(volumes)
        / len(volumes)
        if volumes
        else 1
    )

    large_trades = sum(
        1
        for v in volumes[-20:]
        if v > avg_vol * 1.5
    )

    whale_activity = (
        large_trades / 20 * 100
    )

    if (
        whale_activity > 30
        and closes[-1] > closes[-5]
    ):

        action = "BUY"
        confidence = 75

    elif (
        whale_activity > 30
        and closes[-1] < closes[-5]
    ):

        action = "SELL"
        confidence = 75

    else:

        action = "WAIT"
        confidence = 50

    entry, sl, tp, sr = trade_levels(
        klines,
        action,
        1.05,
        1.10,
    )

    rsi = calculate_rsi(
        closes
    )

    analysis = (
        f"🐋 <b>تحليل الحيتان - {symbol}/USDT</b>\n\n"
        f"نشاط الحجم الكبير: <b>{whale_activity:.1f}%</b>\n"
        f"الشموع ذات الحجم الكبير: <b>{large_trades}/20</b>\n"
        f"RSI: <b>{rsi:.1f}</b>\n\n"
        f"التوصية: <b>{action_text(action)}</b>\n"
        f"الثقة: <b>{confidence}%</b>\n\n"
        f"💡 الدخول: {', '.join(f'${x}' for x in entry)}\n"
        f"🛑 الوقف: ${sl}\n"
        f"🎯 الأهداف: {', '.join(f'${x}' for x in tp)}"
    )

    return {
        "analysis": analysis,
        "action": action,
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "sr": sr,
        "rsi": rsi,
    }


def tvl_analysis(
    klines,
    symbol,
):

    closes = [
        k["close"]
        for k in klines
    ]

    volumes = [
        k["volume"]
        for k in klines
    ]

    avg_vol = (
        sum(volumes[-30:]) / 30
        if len(volumes) >= 30
        else (
            sum(volumes)
            / max(len(volumes), 1)
        )
    )

    recent_vol = (
        sum(volumes[-7:]) / 7
        if len(volumes) >= 7
        else avg_vol
    )

    liquidity_ratio = (
        recent_vol / avg_vol
        if avg_vol
        else 1
    )

    if (
        liquidity_ratio > 1.2
        and closes[-1] > closes[-10]
    ):

        action = "BUY"
        confidence = 70

    elif liquidity_ratio < 0.8:

        action = "SELL"
        confidence = 65

    else:

        action = "WAIT"
        confidence = 50

    entry, sl, tp, sr = trade_levels(
        klines,
        action,
        1.04,
        1.07,
    )

    rsi = calculate_rsi(
        closes
    )

    analysis = (
        f"🔒 <b>تحليل TVL - {symbol}/USDT</b>\n\n"
        f"نسبة السيولة: <b>{liquidity_ratio:.2f}x</b>\n"
        f"متوسط الحجم الأخير: <b>{recent_vol:.2f}</b>\n"
        f"RSI: <b>{rsi:.1f}</b>\n\n"
        f"التوصية: <b>{action_text(action)}</b>\n"
        f"الثقة: <b>{confidence}%</b>\n\n"
        f"💡 الدخول: {', '.join(f'${x}' for x in entry)}\n"
        f"🛑 الوقف: ${sl}\n"
        f"🎯 الأهداف: {', '.join(f'${x}' for x in tp)}"
    )

    return {
        "analysis": analysis,
        "action": action,
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "sr": sr,
        "rsi": rsi,
    }


def analyze_by_school(
    klines,
    symbol,
    school_id,
):

    functions = {
        "wyckoff": wyckoff_analysis,
        "elliott": elliott_analysis,
        "harmonic": harmonic_analysis,
        "classic": classic_analysis,
        "whales": whales_analysis,
        "tvl": tvl_analysis,
    }

    fn = functions.get(
        school_id,
        classic_analysis,
    )

    return fn(
        klines,
        symbol,
    )


# ============================================================
# Chart
# ============================================================

def create_chart(
    klines,
    symbol,
    school_name,
    signal,
):

    fig, ax = plt.subplots(
        figsize=(12, 8)
    )

    dates = [
        k["time"]
        for k in klines
    ]

    opens = [
        k["open"]
        for k in klines
    ]

    highs = [
        k["high"]
        for k in klines
    ]

    lows = [
        k["low"]
        for k in klines
    ]

    closes = [
        k["close"]
        for k in klines
    ]

    for i in range(
        len(klines)
    ):

        if closes[i] >= opens[i]:
            color = "#26a69a"
        else:
            color = "#ef5350"

        ax.plot(
            [dates[i], dates[i]],
            [
                lows[i],
                highs[i],
            ],
            color=color,
            linewidth=1,
        )

        ax.plot(
            [dates[i], dates[i]],
            [
                opens[i],
                closes[i],
            ],
            color=color,
            linewidth=5,
        )

    sr = signal.get(
        "sr",
        {},
    )

    for support in sr.get(
        "supports",
        [],
    ):

        ax.axhline(
            support,
            color="#4caf50",
            linestyle="--",
            alpha=0.7,
        )

    for resistance in sr.get(
        "resistances",
        [],
    ):

        ax.axhline(
            resistance,
            color="#f44336",
            linestyle="--",
            alpha=0.7,
        )

    for entry in signal.get(
        "entry",
        [],
    ):

        ax.axhline(
            entry,
            color="#ffd700",
            linewidth=1.5,
        )

    ax.axhline(
        signal["stop_loss"],
        color="#ff1744",
        linewidth=1.5,
    )

    for tp in signal.get(
        "take_profit",
        [],
    ):

        ax.axhline(
            tp,
            color="#00e676",
            linewidth=1.5,
        )

    ax.set_title(
        f"{symbol}/USDT - {school_name}",
        fontsize=16,
        fontweight="bold",
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter(
            "%m-%d %H:%M"
        )
    )

    plt.setp(
        ax.xaxis.get_majorticklabels(),
        rotation=45,
    )

    plt.tight_layout()

    buf = io.BytesIO()

    plt.savefig(
        buf,
        format="png",
        dpi=150,
    )

    buf.seek(0)

    plt.close(fig)

    return buf


# ============================================================
# Keyboards
# ============================================================

def back_kb():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 رجوع",
                    callback_data="back_main",
                )
            ]
        ]
    )


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


def schools_kb():

    builder = InlineKeyboardBuilder()

    for sid, school in TRADING_SCHOOLS.items():

        builder.row(
            InlineKeyboardButton(
                text=(
                    f"{school['emoji']} "
                    f"{school['name']}"
                ),
                callback_data=f"school_{sid}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔙 رجوع",
            callback_data="back_main",
        )
    )

    return builder.as_markup()


def timeframes_kb(
    sid: str,
):

    builder = InlineKeyboardBuilder()

    for tf in TRADING_SCHOOLS[
        sid
    ]["timeframes"]:

        builder.row(
            InlineKeyboardButton(
                text=f"⏰ {tf}",
                callback_data=f"tf_{sid}_{tf}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔙 رجوع",
            callback_data="start_analysis",
        )
    )

    return builder.as_markup()


def coins_kb(
    sid: str,
    tf: str,
):

    builder = InlineKeyboardBuilder()

    coins = [
        "BTC",
        "ETH",
        "SOL",
        "BNB",
        "XRP",
        "ADA",
        "DOGE",
        "AVAX",
    ]

    for i in range(
        0,
        len(coins),
        2,
    ):

        row = []

        for coin in coins[
            i:i + 2
        ]:

            row.append(
                InlineKeyboardButton(
                    text=f"💰 {coin}",
                    callback_data=(
                        f"analyze_{sid}_{tf}_{coin}"
                    ),
                )
            )

        builder.row(
            *row
        )

    builder.row(
        InlineKeyboardButton(
            text="🔍 بحث عن عملة",
            callback_data=f"custom_{sid}_{tf}",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔙 رجوع",
            callback_data=f"school_{sid}",
        )
    )

    return builder.as_markup()


def plans_kb():

    builder = InlineKeyboardBuilder()

    for plan_id, plan in PLANS.items():

        builder.row(
            InlineKeyboardButton(
                text=(
                    f"{plan['emoji']} "
                    f"{plan['name']} - "
                    f"{plan['price']} USDT"
                ),
                callback_data=f"subscribe_{plan_id}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔙 رجوع",
            callback_data="back_main",
        )
    )

    return builder.as_markup()


def network_kb(
    plan_id: str,
):

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="◎ USDT — Solana",
            callback_data=f"net_{plan_id}_sol",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="Ξ USDT — Ethereum",
            callback_data=f"net_{plan_id}_eth",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🟡 USDT — BNB Chain",
            callback_data=f"net_{plan_id}_bsc",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔙 رجوع",
            callback_data="plans",
        )
    )

    return builder.as_markup()


def payment_kb(
    payment_id: int,
):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔎 تحقق من الدفع",
                    callback_data=f"checkpay_{payment_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ إلغاء",
                    callback_data=f"cancelpay_{payment_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💎 تغيير الشبكة",
                    callback_data="plans",
                )
            ],
        ]
    )


# ============================================================
# Start
# ============================================================

@dp.message(Command("start"))
async def cmd_start(
    message: Message,
):

    await db.update_username(
        message.from_user.id,
        message.from_user.username,
    )

    await message.answer(
        "🌟 <b>Doshka Trading Pro</b>\n\n"
        "📊 6 مدارس تحليل مختلفة\n"
        "🎯 تحليل مختلف لكل مدرسة\n"
        "💎 اشتراكات USDT تلقائية\n\n"
        "اختر من القائمة:",
        reply_markup=main_kb(),
    )


# ============================================================
# Main
# ============================================================

@dp.callback_query(
    F.data == "back_main"
)
async def back_main(
    callback: CallbackQuery,
    state: FSMContext,
):

    await state.clear()

    await callback.message.edit_text(
        "🌟 <b>Doshka Trading Pro</b>\n\n"
        "اختر من القائمة:",
        reply_markup=main_kb(),
    )

    await callback.answer()


# ============================================================
# Analysis
# ============================================================

@dp.callback_query(
    F.data == "start_analysis"
)
async def start_analysis(
    callback: CallbackQuery,
):

    if not await db.is_subscribed(
        callback.from_user.id
    ):

        await callback.answer(
            "❌ هذه الخدمة للمشتركين فقط.",
            show_alert=True,
        )

        return

    text = (
        "<b>📊 اختر مدرسة التحليل:</b>\n\n"
    )

    for school in TRADING_SCHOOLS.values():

        text += (
            f"{school['emoji']} "
            f"<b>{school['name']}</b>\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=schools_kb(),
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("school_")
)
async def choose_school(
    callback: CallbackQuery,
):

    sid = callback.data.split(
        "_",
        1,
    )[1]

    if sid not in TRADING_SCHOOLS:

        await callback.answer(
            "❌ مدرسة غير معروفة.",
            show_alert=True,
        )

        return

    school = TRADING_SCHOOLS[
        sid
    ]

    await callback.message.edit_text(
        (
            f"{school['emoji']} "
            f"<b>{school['name']}</b>\n\n"
            "اختر الفترة الزمنية:"
        ),
        reply_markup=timeframes_kb(
            sid
        ),
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("tf_")
)
async def choose_tf(
    callback: CallbackQuery,
):

    parts = callback.data.split(
        "_"
    )

    if len(parts) != 3:

        await callback.answer(
            "❌ طلب غير صالح.",
            show_alert=True,
        )

        return

    sid = parts[1]
    tf = parts[2]

    if sid not in TRADING_SCHOOLS:

        await callback.answer(
            "❌ مدرسة غير صالحة.",
            show_alert=True,
        )

        return

    if tf not in TRADING_SCHOOLS[
        sid
    ]["timeframes"]:

        await callback.answer(
            "❌ فترة زمنية غير صالحة.",
            show_alert=True,
        )

        return

    await callback.message.edit_text(
        "💰 <b>اختر العملة:</b>",
        reply_markup=coins_kb(
            sid,
            tf,
        ),
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("custom_")
)
async def custom_symbol(
    callback: CallbackQuery,
    state: FSMContext,
):

    parts = callback.data.split(
        "_"
    )

    if len(parts) != 3:
        await callback.answer(
            "❌ طلب غير صالح.",
            show_alert=True,
        )
        return

    sid = parts[1]
    tf = parts[2]

    await state.update_data(
        sid=sid,
        tf=tf,
    )

    await state.set_state(
        AnalysisStates.waiting_for_custom_symbol
    )

    await callback.message.edit_text(
        (
            "🔍 <b>أدخل رمز العملة</b>\n\n"
            "مثال:\n"
            "<code>BTC</code>\n"
            "<code>ETH</code>\n"
            "<code>SOL</code>"
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ إلغاء",
                        callback_data="back_main",
                    )
                ]
            ]
        ),
    )

    await callback.answer()


@dp.message(
    StateFilter(
        AnalysisStates.waiting_for_custom_symbol
    )
)
async def process_custom(
    message: Message,
    state: FSMContext,
):

    data = await state.get_data()

    sid = data.get(
        "sid"
    )

    tf = data.get(
        "tf"
    )

    symbol = (
        message.text
        .strip()
        .upper()
        .replace(
            "/USDT",
            "",
        )
        .replace(
            "USDT",
            "",
        )
    )

    await state.clear()

    if not symbol:

        await message.answer(
            "❌ رمز العملة غير صالح.",
            reply_markup=main_kb(),
        )

        return

    await do_analysis(
        message,
        symbol,
        sid,
        tf,
    )


@dp.callback_query(
    F.data.startswith("analyze_")
)
async def analyze_cb(
    callback: CallbackQuery,
):

    parts = callback.data.split(
        "_"
    )

    if len(parts) != 4:

        await callback.answer(
            "❌ طلب غير صالح.",
            show_alert=True,
        )

        return

    sid = parts[1]
    tf = parts[2]
    symbol = parts[3]

    if not await db.is_subscribed(
        callback.from_user.id
    ):

        await callback.answer(
            "❌ الاشتراك مطلوب.",
            show_alert=True,
        )

        return

    await callback.answer(
        "⏳ جاري التحليل..."
    )

    await do_analysis(
        callback.message,
        symbol,
        sid,
        tf,
    )


async def do_analysis(
    message: Message,
    symbol: str,
    sid: str,
    tf: str,
):

    if sid not in TRADING_SCHOOLS:

        await message.answer(
            "❌ مدرسة غير صالحة."
        )

        return

    school_name = (
        TRADING_SCHOOLS[sid]["name"]
    )

    wait = await message.answer(
        f"⏳ جاري تحليل "
        f"<b>{symbol}/USDT</b> "
        f"بمدرسة <b>{school_name}</b>..."
    )

    klines = await get_klines(
        symbol,
        tf,
        100,
    )

    if len(klines) < 30:

        await wait.edit_text(
            (
                f"❌ لم أستطع الحصول على "
                f"بيانات كافية لـ "
                f"<b>{symbol}/USDT</b>.\n\n"
                "تأكد أن العملة مدرجة في Binance."
            )
        )

        return

    try:

        signal = analyze_by_school(
            klines,
            symbol,
            sid,
        )

        chart = create_chart(
            klines,
            symbol,
            school_name,
            signal,
        )

        await wait.delete()

        await message.answer_photo(
            photo=BufferedInputFile(
                chart.read(),
                filename=(
                    f"{symbol}_{sid}.png"
                ),
            ),
            caption=signal["analysis"],
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📊 تحليل آخر",
                            callback_data="start_analysis",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔙 الرئيسية",
                            callback_data="back_main",
                        )
                    ],
                ]
            ),
        )

    except Exception:

        logger.exception(
            "Analysis error"
        )

        await wait.edit_text(
            "❌ حدث خطأ أثناء إنشاء التحليل."
        )


# ============================================================
# Plans
# ============================================================

@dp.callback_query(
    F.data == "plans"
)
async def show_plans(
    callback: CallbackQuery,
    state: FSMContext,
):

    await state.clear()

    text = (
        "<b>💎 خطط الاشتراك</b>\n\n"
        "الدفع متاح بعملة <b>USDT فقط</b>.\n\n"
    )

    for plan in PLANS.values():

        text += (
            f"{plan['emoji']} "
            f"<b>{plan['name']}</b> — "
            f"<b>{plan['price']} USDT</b>\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=plans_kb(),
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("subscribe_")
)
async def subscribe_plan(
    callback: CallbackQuery,
):

    plan_id = callback.data.split(
        "_",
        1,
    )[1]

    if plan_id not in PLANS:

        await callback.answer(
            "❌ باقة غير صالحة.",
            show_alert=True,
        )

        return

    plan = PLANS[
        plan_id
    ]

    await callback.message.edit_text(
        (
            f"💳 <b>{plan['name']}</b>\n\n"
            f"💰 السعر: <b>{plan['price']} USDT</b>\n\n"
            "اختر شبكة إرسال USDT:"
        ),
        reply_markup=network_kb(
            plan_id
        ),
    )

    await callback.answer()


# ============================================================
# Create payment session
# ============================================================

@dp.callback_query(
    F.data.startswith("net_")
)
async def choose_network(
    callback: CallbackQuery,
):

    parts = callback.data.split(
        "_"
    )

    if len(parts) != 3:

        await callback.answer(
            "❌ طلب غير صالح.",
            show_alert=True,
        )

        return

    plan_id = parts[1]
    network = parts[2]

    if plan_id not in PLANS:

        await callback.answer(
            "❌ الباقة غير صالحة.",
            show_alert=True,
        )

        return

    if network not in NETWORKS:

        await callback.answer(
            "❌ الشبكة غير صالحة.",
            show_alert=True,
        )

        return

    # منع إنشاء عشرات جلسات الدفع
    # لنفس المستخدم.
    existing = await db.get_pending_payments(
        network
    )

    for p in existing:

        if (
            p["user_id"]
            == callback.from_user.id
        ):

            await callback.message.edit_text(
                (
                    "⚠️ لديك عملية دفع قيد الانتظار "
                    "على هذه الشبكة بالفعل.\n\n"
                    "استخدم زر التحقق من الدفع "
                    "أو ألغ العملية السابقة."
                ),
                reply_markup=payment_kb(
                    p["id"]
                ),
            )

            await callback.answer()

            return

    payment_id = await db.create_payment(
        callback.from_user.id,
        plan_id,
        network,
    )

    plan = PLANS[
        plan_id
    ]

    cfg = NETWORKS[
        network
    ]

    await callback.message.edit_text(
        (
            "💳 <b>طلب دفع USDT</b>\n\n"
            f"📦 الباقة: <b>{plan['name']}</b>\n"
            f"💰 المبلغ المطلوب: <b>{plan['price']} USDT</b>\n"
            f"🌐 الشبكة: <b>{cfg['name']}</b>\n\n"
            "📮 <b>أرسل USDT إلى العنوان التالي:</b>\n"
            f"<code>{cfg['wallet']}</code>\n\n"
            "⚠️ <b>مهم جداً:</b>\n"
            "أرسل USDT فقط على الشبكة المختارة.\n"
            "لا ترسل ETH أو BNB أو SOL.\n\n"
            "🤖 لا تحتاج إلى إرسال Transaction Hash.\n"
            "سيقوم البوت بمراقبة الشبكة تلقائياً.\n\n"
            f"⏱️ صلاحية الطلب: <b>{PAYMENT_TIMEOUT_MINUTES} دقيقة</b>"
        ),
        reply_markup=payment_kb(
            payment_id
        ),
    )

    await callback.answer()


# ============================================================
# Check payment manually - WITHOUT HASH
# ============================================================

@dp.callback_query(
    F.data.startswith("checkpay_")
)
async def check_payment(
    callback: CallbackQuery,
):

    try:

        payment_id = int(
            callback.data.split(
                "_"
            )[1]
        )

    except Exception:

        await callback.answer(
            "❌ طلب غير صالح.",
            show_alert=True,
        )

        return

    payment = await db.get_payment(
        payment_id
    )

    if not payment:

        await callback.answer(
            "❌ عملية الدفع غير موجودة.",
            show_alert=True,
        )

        return

    if (
        payment["user_id"]
        != callback.from_user.id
    ):

        await callback.answer(
            "❌ هذه العملية ليست لك.",
            show_alert=True,
        )

        return

    if payment["status"] == "paid":

        await callback.answer(
            "✅ الدفع مؤكد بالفعل.",
            show_alert=True,
        )

        return

    if payment["status"] == "expired":

        await callback.answer(
            "❌ انتهت صلاحية عملية الدفع.",
            show_alert=True,
        )

        return

    await callback.answer(
        "🔎 البوت يبحث الآن في الشبكة..."
    )

    # نعطي رسالة بسيطة، والمراقب الخلفي
    # سيكمل الفحص تلقائياً.
    await callback.message.edit_text(
        (
            "🔎 <b>جاري التحقق من الدفع...</b>\n\n"
            "لا تحتاج إلى إرسال Transaction Hash.\n"
            "سيتم فحص شبكة الدفع تلقائياً.\n\n"
            "إذا كانت المعاملة صحيحة ومؤكدة، "
            "سيتم تفعيل اشتراكك تلقائياً."
        ),
        reply_markup=payment_kb(
            payment_id
        ),
    )


# ============================================================
# Cancel payment
# ============================================================

@dp.callback_query(
    F.data.startswith("cancelpay_")
)
async def cancel_payment(
    callback: CallbackQuery,
):

    try:

        payment_id = int(
            callback.data.split(
                "_"
            )[1]
        )

    except Exception:

        await callback.answer(
            "❌ طلب غير صالح.",
            show_alert=True,
        )

        return

    payment = await db.get_payment(
        payment_id
    )

    if not payment:

        await callback.answer(
            "❌ العملية غير موجودة.",
            show_alert=True,
        )

        return

    if (
        payment["user_id"]
        != callback.from_user.id
    ):

        await callback.answer(
            "❌ هذه العملية ليست لك.",
            show_alert=True,
        )

        return

    if payment["status"] == "paid":

        await callback.answer(
            "❌ لا يمكن إلغاء عملية مدفوعة.",
            show_alert=True,
        )

        return

    conn = db.connect()

    conn.execute(
        """
        UPDATE payments
        SET status='cancelled'
        WHERE id=?
        AND user_id=?
        AND status='pending'
        """,
        (
            payment_id,
            callback.from_user.id,
        ),
    )

    conn.commit()
    conn.close()

    await callback.message.edit_text(
        (
            "❌ <b>تم إلغاء عملية الدفع.</b>\n\n"
            "لم يتم تفعيل أي اشتراك."
        ),
        reply_markup=plans_kb(),
    )

    await callback.answer()


# ============================================================
# Status
# ============================================================

@dp.callback_query(
    F.data == "status"
)
async def check_status(
    callback: CallbackQuery,
):

    uid = callback.from_user.id

    if uid == ADMIN_ID:

        text = (
            "👑 <b>حساب الإدارة</b>\n\n"
            "الوصول إلى البوت مفعل دائماً."
        )

    else:

        sub = await db.get_user_subscription(
            uid
        )

        if not sub or not sub.get(
            "expire_date"
        ):

            text = (
                "❌ <b>لا يوجد اشتراك نشط.</b>\n\n"
                "يمكنك اختيار باقة من الاشتراكات."
            )

        else:

            try:

                expire = datetime.fromisoformat(
                    sub["expire_date"]
                )

                if expire > datetime.now():

                    plan_name = PLANS.get(
                        sub["plan"],
                        {},
                    ).get(
                        "name",
                        sub["plan"],
                    )

                    text = (
                        "✅ <b>اشتراكك نشط</b>\n\n"
                        f"📦 الباقة: <b>{plan_name}</b>\n"
                        f"📅 ينتهي: <b>{expire.strftime('%Y-%m-%d %H:%M')}</b>"
                    )

                else:

                    text = (
                        "❌ <b>انتهى اشتراكك.</b>"
                    )

            except Exception:

                text = (
                    "❌ <b>لا يوجد اشتراك نشط.</b>"
                )

    await callback.message.edit_text(
        text,
        reply_markup=back_kb(),
    )

    await callback.answer()


# ============================================================
# Help
# ============================================================

@dp.callback_query(
    F.data == "help"
)
async def help_cb(
    callback: CallbackQuery,
):

    text = (
        "<b>📖 Doshka Trading Pro</b>\n\n"
        "📊 <b>وايكوف</b> — العرض والطلب والحجم\n"
        "🌊 <b>إليوت</b> — الموجات\n"
        "🦋 <b>هارمونيك</b> — الأنماط التوافقية\n"
        "📈 <b>كلاسيكي</b> — RSI وMACD\n"
        "🐋 <b>الحيتان</b> — نشاط الحجم\n"
        "🔒 <b>TVL</b> — تحليل السيولة\n\n"
        "<b>الدفع:</b>\n"
        "💵 USDT فقط\n"
        "◎ Solana\n"
        "Ξ Ethereum\n"
        "🟡 BNB Smart Chain\n\n"
        "🤖 لا تحتاج إلى إرسال Transaction Hash.\n"
        "البوت يتحقق من الشبكة تلقائياً."
    )

    await callback.message.edit_text(
        text,
        reply_markup=back_kb(),
    )

    await callback.answer()


# ============================================================
# Admin commands
# ============================================================

@dp.message(Command("admin"))
async def admin_command(
    message: Message,
):

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "❌ غير مصرح."
        )

        return

    pending = await db.get_pending_payments()

    text = (
        "👑 <b>لوحة الإدارة</b>\n\n"
        f"💳 عمليات الدفع المعلقة: <b>{len(pending)}</b>\n"
        f"🌐 ETH RPC: <b>{'OK' if ETH_RPC_URL else 'NO'}</b>\n"
        f"🟡 BSC RPC: <b>{'OK' if BSC_RPC_URL else 'NO'}</b>\n"
        f"◎ SOL RPC: <b>{'OK' if SOL_RPC_URL else 'NO'}</b>"
    )

    await message.answer(
        text
    )


# ============================================================
# Error handler
# ============================================================

@dp.errors()
async def global_error_handler(
    event,
):

    logger.exception(
        "Unhandled aiogram error: %s",
        event.exception,
    )

    return True


# ============================================================
# Main
# ============================================================

async def main():

    await db.init()

    logger.info(
        "🚀 Doshka Trading Pro starting..."
    )

    logger.info(
        "ETH wallet: %s",
        ETH_WALLET,
    )

    logger.info(
        "BSC wallet: %s",
        BSC_WALLET,
    )

    logger.info(
        "SOL wallet: %s",
        SOL_WALLET,
    )

    logger.info(
        "Payment monitor interval: %s seconds",
        PAYMENT_SCAN_SECONDS,
    )

    # تشغيل مراقب الدفع في الخلفية
    payment_task = asyncio.create_task(
        payment_monitor()
    )

    try:

        await bot.delete_webhook(
            drop_pending_updates=True
        )

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )

    finally:

        payment_task.cancel()

        try:
            await payment_task
        except asyncio.CancelledError:
            pass

        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(
            main()
        )
    except KeyboardInterrupt:
        logger.info(
            "Bot stopped."
        )
