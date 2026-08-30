
from __future__ import annotations

import asyncio
import base64
import json
import time
from datetime import datetime, timezone
from typing import Any

import aiohttp

from config import (
    NETWORKS,
    PAYMENT_LOOKBACK_BLOCKS_EVM,
    PAYMENT_LOOKBACK_SIGNATURES_SOL,
    PAYMENT_MIN_CONFIRMATIONS,
)

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _norm_hex(value: str) -> str:
    return value.lower().replace("0x", "").strip()


def _wallet_topic(wallet: str) -> str:
    return "0x" + ("0" * 24) + _norm_hex(wallet)


def _within(amount: float, expected: float) -> bool:
    # Orders use simple USDT prices. Allow a tiny precision margin.
    return abs(amount - expected) <= max(0.00001, expected * 0.000001)


async def _rpc(url: str, method: str, params: list[Any]) -> Any:
    timeout = aiohttp.ClientTimeout(total=20)
    payload = {"jsonrpc": "2.0", "id": int(time.time() * 1000) % 1000000, "method": method, "params": params}
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                raise RuntimeError(f"RPC HTTP {response.status}")
            data = await response.json()
    if "error" in data:
        raise RuntimeError(str(data["error"]))
    return data.get("result")


async def _evm_payment(order: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any] | None:
    wallet = cfg["wallet"]
    token = cfg["token"]
    expected = float(order["amount"])
    decimals = int(cfg["decimals"])
    created_ts = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00")).timestamp()

    latest_hex = await _rpc(cfg["rpc"], "eth_blockNumber", [])
    latest = int(latest_hex, 16)
    from_block = max(0, latest - PAYMENT_LOOKBACK_BLOCKS_EVM)

    # topic0=Transfer, topic2=recipient. This ensures the destination is OUR configured wallet.
    logs = await _rpc(
        cfg["rpc"],
        "eth_getLogs",
        [{
            "fromBlock": hex(from_block),
            "toBlock": hex(latest),
            "address": token,
            "topics": [TRANSFER_TOPIC, None, _wallet_topic(wallet)],
        }],
    )

    for log in reversed(logs or []):
        tx_id = log.get("transactionHash")
        if not tx_id:
            continue

        block_hex = log.get("blockNumber", "0x0")
        block_number = int(block_hex, 16)
        raw = int(log.get("data", "0x0"), 16)
        amount = raw / (10 ** decimals)
        if not _within(amount, expected):
            continue

        tx = await _rpc(cfg["rpc"], "eth_getTransactionByHash", [tx_id])
        if not tx:
            continue

        # For a token transfer, the transaction's timestamp isn't in the tx itself.
        block = await _rpc(cfg["rpc"], "eth_getBlockByNumber", [block_hex, False])
        if not block:
            continue
        block_time = int(block.get("timestamp", "0x0"), 16)
        if block_time < created_ts - 120:
            continue

        confirmations = latest - block_number + 1
        if confirmations < PAYMENT_MIN_CONFIRMATIONS:
            continue

        receipt = await _rpc(cfg["rpc"], "eth_getTransactionReceipt", [tx_id])
        if not receipt or receipt.get("status") != "0x1":
            continue

        return {
            "tx_id": tx_id,
            "amount": amount,
            "confirmations": confirmations,
            "timestamp": datetime.fromtimestamp(block_time, tz=timezone.utc),
        }

    return None


def _lamports_amount(balance: dict[str, Any]) -> float:
    raw = int(balance.get("uiTokenAmount", {}).get("amount", "0"))
    decimals = int(balance.get("uiTokenAmount", {}).get("decimals", 6))
    return raw / (10 ** decimals)


async def _solana_payment(order: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any] | None:
    wallet = cfg["wallet"]
    mint = cfg["token"]
    expected = float(order["amount"])
    created_ts = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00")).timestamp()

    token_accounts = await _rpc(
        cfg["rpc"],
        "getTokenAccountsByOwner",
        [
            wallet,
            {"mint": mint, "encoding": "jsonParsed"},
        ],
    )
    addresses = [
        item.get("pubkey")
        for item in (token_accounts or {}).get("value", [])
        if item.get("pubkey")
    ]
    if not addresses:
        return None

    collected = {}
    per_account_limit = max(20, PAYMENT_LOOKBACK_SIGNATURES_SOL // max(1, len(addresses)))
    for token_account in addresses:
        sigs = await _rpc(
            cfg["rpc"],
            "getSignaturesForAddress",
            [token_account, {"limit": per_account_limit}],
        )
        for item in sigs or []:
            collected[item.get("signature")] = item

    signatures = sorted(
        [x for x in collected.values() if x.get("signature")],
        key=lambda x: x.get("blockTime") or 0,
        reverse=True,
    )

    for item in signatures:
        if item.get("err") is not None:
            continue
        block_time = item.get("blockTime")
        if block_time is not None and block_time < created_ts - 120:
            continue

        signature = item.get("signature")
        if not signature:
            continue

        tx = await _rpc(
            cfg["rpc"],
            "getTransaction",
            [
                signature,
                {
                    "encoding": "jsonParsed",
                    "commitment": "confirmed",
                    "maxSupportedTransactionVersion": 0,
                },
            ],
        )
        if not tx:
            continue

        meta = tx.get("meta") or {}
        if meta.get("err") is not None:
            continue

        pre = meta.get("preTokenBalances") or []
        post = meta.get("postTokenBalances") or []

        def owned_by_wallet(entry):
            return (
                entry.get("mint") == mint
                and entry.get("owner") == wallet
            )

        pre_map = {}
        post_map = {}
        for entry in pre:
            if owned_by_wallet(entry):
                pre_map[entry.get("accountIndex")] = _lamports_amount(entry)
        for entry in post:
            if owned_by_wallet(entry):
                post_map[entry.get("accountIndex")] = _lamports_amount(entry)

        delta = 0.0
        for key in set(pre_map) | set(post_map):
            delta += post_map.get(key, 0.0) - pre_map.get(key, 0.0)

        if _within(delta, expected):
            confirmation = item.get("confirmationStatus")
            if confirmation not in ("confirmed", "finalized"):
                continue
            return {
                "tx_id": signature,
                "amount": delta,
                "confirmations": 1 if confirmation == "confirmed" else 2,
                "timestamp": datetime.fromtimestamp(
                    block_time or time.time(), tz=timezone.utc
                ),
            }
    return None


async def find_payment(order: dict[str, Any]) -> dict[str, Any] | None:
    cfg = NETWORKS.get(order["network"])
    if not cfg or not cfg.get("wallet"):
        return None
    if cfg["kind"] == "evm":
        return await _evm_payment(order, cfg)
    if cfg["kind"] == "solana":
        return await _solana_payment(order, cfg)
    return None
