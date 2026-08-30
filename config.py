
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def required_env(name: str) -> str:
    value = env(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def int_env(name: str, default: int = 0) -> int:
    raw = env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def float_env(name: str, default: float = 0.0) -> float:
    raw = env(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number") from exc


@dataclass(frozen=True)
class Plan:
    name: str
    price: float
    days: int
    emoji: str


BASE_DIR = Path(__file__).resolve().parent
SQLITE_PATH = env("SQLITE_PATH", str(BASE_DIR / "data" / "doshka.db"))

BOT_TOKEN = required_env("BOT_TOKEN")
ADMIN_ID = int_env("ADMIN_ID", 0)

PAYMENT_SCAN_SECONDS = max(15, int_env("PAYMENT_SCAN_SECONDS", 45))
ORDER_TTL_MINUTES = max(5, int_env("ORDER_TTL_MINUTES", 30))
PAYMENT_MIN_CONFIRMATIONS = max(1, int_env("PAYMENT_MIN_CONFIRMATIONS", 2))
PAYMENT_LOOKBACK_BLOCKS_EVM = max(100, int_env("PAYMENT_LOOKBACK_BLOCKS_EVM", 1200))
PAYMENT_LOOKBACK_SIGNATURES_SOL = max(20, int_env("PAYMENT_LOOKBACK_SIGNATURES_SOL", 100))

BINANCE_API_BASE = env("BINANCE_API_BASE", "https://api.binance.com")
BINANCE_TIMEOUT_SECONDS = max(5, int_env("BINANCE_TIMEOUT_SECONDS", 15))

PLANS = {
    "1m": Plan("اشتراك شهر", 10.0, 30, "🥉"),
    "3m": Plan("اشتراك 3 أشهر", 25.0, 90, "🥈"),
    "6m": Plan("اشتراك 6 أشهر", 45.0, 180, "🥇"),
    "1y": Plan("اشتراك سنة", 75.0, 365, "💎"),
}


# IMPORTANT:
# These are the addresses that receive funds. The scanner uses the SAME values.
# Put only YOUR public receiving addresses here. Never put private keys in Railway.
NETWORKS = {
    "eth": {
        "name": "Ethereum (ERC20)",
        "wallet": env("ETH_WALLET"),
        "rpc": env("ETH_RPC_URL", "https://ethereum-rpc.publicnode.com"),
        "token": env(
            "ETH_USDT_CONTRACT",
            "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        ),
        "decimals": 6,
        "explorer": "https://etherscan.io/tx/",
        "kind": "evm",
    },
    "bnb": {
        "name": "BNB Smart Chain",
        "wallet": env("BSC_WALLET"),
        "rpc": env("BSC_RPC_URL", "https://bsc-rpc.publicnode.com"),
        # Common BSC USDT contract. Keep configurable because token deployments can change.
        "token": env(
            "BSC_USDT_CONTRACT",
            "0x55d398326f99059ff775485246999027b3197955",
        ),
        "decimals": 18,
        "explorer": "https://bscscan.com/tx/",
        "kind": "evm",
    },
    "sol": {
        "name": "Solana",
        "wallet": env("SOL_WALLET"),
        "rpc": env("SOL_RPC_URL", "https://api.mainnet-beta.solana.com"),
        "token": env(
            "SOL_USDT_MINT",
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        ),
        "decimals": 6,
        "explorer": "https://solscan.io/tx/",
        "kind": "solana",
    },
}

COINS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "ADA",
    "DOGE", "AVAX", "LINK", "DOT", "TRX", "LTC",
]

SCHOOLS = {
    "wyckoff": {
        "name": "وايكوف",
        "emoji": "📊",
        "timeframes": ["15m", "1h", "4h", "1d"],
    },
    "elliott": {
        "name": "إليوت",
        "emoji": "🌊",
        "timeframes": ["1h", "4h", "1d"],
    },
    "harmonic": {
        "name": "هارمونيك",
        "emoji": "🦋",
        "timeframes": ["15m", "1h", "4h"],
    },
    "classic": {
        "name": "التحليل الكلاسيكي",
        "emoji": "📈",
        "timeframes": ["5m", "15m", "1h", "4h", "1d"],
    },
    "whales": {
        "name": "الحيتان",
        "emoji": "🐋",
        "timeframes": ["5m", "15m", "1h", "4h"],
    },
    "liquidity": {
        "name": "السيولة",
        "emoji": "🔒",
        "timeframes": ["5m", "15m", "1h", "4h"],
    },
}

def validate_public_config() -> None:
    missing = []
    for key in ("eth", "bnb", "sol"):
        if not NETWORKS[key]["wallet"]:
            missing.append(f"{key.upper()}_WALLET")
    if ADMIN_ID <= 0:
        missing.append("ADMIN_ID")
    if missing:
        raise RuntimeError("Missing configuration: " + ", ".join(missing))
