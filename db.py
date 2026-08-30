
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from config import PLANS


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class Database:
    def __init__(self, path: str):
        self.path = path
        self._lock = asyncio.Lock()

    async def init(self, admin_id: int) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        async with self._connect() as db:
            await db.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;

                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    user_id INTEGER PRIMARY KEY,
                    plan TEXT NOT NULL,
                    expire_date TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    plan TEXT NOT NULL,
                    network TEXT NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    network TEXT NOT NULL,
                    tx_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    order_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(network, tx_id)
                );

                CREATE INDEX IF NOT EXISTS idx_orders_user_status
                    ON orders(user_id, status, expires_at);
                CREATE INDEX IF NOT EXISTS idx_orders_pending
                    ON orders(status, expires_at);
                """
            )
            await db.commit()

        # Admin is always active in the application.
        if admin_id > 0:
            await self.upsert_user(admin_id, "admin")
            await self.activate(admin_id, "1y")

    def _connect(self) -> aiosqlite.Connection:
        return aiosqlite.connect(self.path)

    async def upsert_user(self, user_id: int, username: str | None) -> None:
        now = iso(utcnow())
        async with self._lock:
            async with self._connect() as db:
                await db.execute(
                    """
                    INSERT INTO users(user_id, username, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username=excluded.username,
                        updated_at=excluded.updated_at
                    """,
                    (user_id, username, now, now),
                )
                await db.commit()

    async def active(self, user_id: int, admin_id: int) -> bool:
        if user_id == admin_id and admin_id > 0:
            return True
        async with self._connect() as db:
            async with db.execute(
                "SELECT expire_date FROM subscriptions WHERE user_id=?",
                (user_id,),
            ) as cur:
                row = await cur.fetchone()
        return bool(row and parse_dt(row[0]) > utcnow())

    async def create_order(self, user_id: int, plan: str, network: str, ttl_minutes: int):
        if plan not in PLANS:
            raise ValueError("Invalid plan")
        now = utcnow()
        expires = now + timedelta(minutes=ttl_minutes)
        order_id = uuid.uuid4().hex[:12].upper()
        async with self._lock:
            async with self._connect() as db:
                await db.execute(
                    """
                    UPDATE orders
                    SET status='cancelled'
                    WHERE user_id=? AND status='pending'
                    """,
                    (user_id,),
                )
                await db.execute(
                    """
                    INSERT INTO orders
                    (id,user_id,plan,network,amount,status,created_at,expires_at)
                    VALUES (?,?,?,?,?,?,?,?)
                    """,
                    (
                        order_id,
                        user_id,
                        plan,
                        network,
                        PLANS[plan].price,
                        "pending",
                        iso(now),
                        iso(expires),
                    ),
                )
                await db.commit()
        return order_id, now, expires

    async def pending(self, user_id: int) -> dict[str, Any] | None:
        async with self._connect() as db:
            async with db.execute(
                """
                SELECT id,user_id,plan,network,amount,status,created_at,expires_at
                FROM orders
                WHERE user_id=? AND status='pending'
                ORDER BY created_at DESC LIMIT 1
                """,
                (user_id,),
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return None
        order = self._order(row)
        if parse_dt(order["expires_at"]) <= utcnow():
            await self.mark_order(order["id"], "expired")
            return None
        return order

    async def pending_batch(self, limit: int = 25) -> list[dict[str, Any]]:
        async with self._connect() as db:
            async with db.execute(
                """
                SELECT id,user_id,plan,network,amount,status,created_at,expires_at
                FROM orders
                WHERE status='pending' AND expires_at > ?
                ORDER BY created_at ASC LIMIT ?
                """,
                (iso(utcnow()), limit),
            ) as cur:
                rows = await cur.fetchall()
        return [self._order(row) for row in rows]

    async def expire_old_orders(self) -> None:
        async with self._lock:
            async with self._connect() as db:
                await db.execute(
                    "UPDATE orders SET status='expired' WHERE status='pending' AND expires_at <= ?",
                    (iso(utcnow()),),
                )
                await db.commit()

    async def mark_order(self, order_id: str, status: str) -> None:
        async with self._lock:
            async with self._connect() as db:
                await db.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
                await db.commit()

    async def claim_transaction(
        self, network: str, tx_id: str, user_id: int, order_id: str, amount: float
    ) -> bool:
        async with self._lock:
            async with self._connect() as db:
                try:
                    await db.execute(
                        """
                        INSERT INTO transactions
                        (network,tx_id,user_id,order_id,amount,created_at)
                        VALUES (?,?,?,?,?,?)
                        """,
                        (network, tx_id, user_id, order_id, amount, iso(utcnow())),
                    )
                    await db.execute(
                        "UPDATE orders SET status='paid' WHERE id=? AND status='pending'",
                        (order_id,),
                    )
                    await db.commit()
                    return True
                except aiosqlite.IntegrityError:
                    return False

    async def activate(self, user_id: int, plan: str) -> datetime:
        if plan not in PLANS:
            raise ValueError("Invalid plan")
        now = utcnow()
        async with self._lock:
            async with self._connect() as db:
                async with db.execute(
                    "SELECT expire_date FROM subscriptions WHERE user_id=?",
                    (user_id,),
                ) as cur:
                    row = await cur.fetchone()
                base = max(parse_dt(row[0]), now) if row else now
                expires = base + timedelta(days=PLANS[plan].days)
                await db.execute(
                    """
                    INSERT INTO subscriptions(user_id,plan,expire_date,updated_at)
                    VALUES (?,?,?,?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        plan=excluded.plan,
                        expire_date=excluded.expire_date,
                        updated_at=excluded.updated_at
                    """,
                    (user_id, plan, iso(expires), iso(now)),
                )
                await db.commit()
        return expires

    async def status(self, user_id: int) -> dict[str, Any] | None:
        async with self._connect() as db:
            async with db.execute(
                "SELECT plan,expire_date FROM subscriptions WHERE user_id=?",
                (user_id,),
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return None
        expire = parse_dt(row[1])
        return {"plan": row[0], "expire_date": expire.strftime("%Y-%m-%d %H:%M UTC"), "is_active": expire > utcnow()}

    @staticmethod
    def _order(row) -> dict[str, Any]:
        keys = ["id","user_id","plan","network","amount","status","created_at","expires_at"]
        return dict(zip(keys, row))
