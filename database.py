# database.py

import sqlite3
import asyncio
from datetime import datetime, timedelta

from config import DB_NAME, PLANS


class Database:

    def __init__(self):
        self.lock = asyncio.Lock()


    async def init(self):

        async with self.lock:

            con = sqlite3.connect(DB_NAME)
            cur = con.cursor()

            cur.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY,
                username TEXT,
                plan TEXT DEFAULT 'free',
                spot INTEGER DEFAULT 0,
                futures INTEGER DEFAULT 0,
                alerts INTEGER DEFAULT 0,
                expire TEXT
            )
            """)


            cur.execute("""
            CREATE TABLE IF NOT EXISTS alerts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                created TEXT
            )
            """)


            cur.execute("""
            CREATE TABLE IF NOT EXISTS signals(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                market TEXT,
                action TEXT,
                price REAL,
                created TEXT
            )
            """)


            con.commit()
            con.close()



    async def add_user(self,user_id,username):

        async with self.lock:

            con=sqlite3.connect(DB_NAME)
            cur=con.cursor()

            cur.execute(
            """
            INSERT OR IGNORE INTO users(id,username)
            VALUES(?,?)
            """,
            (user_id,username)
            )

            con.commit()
            con.close()



    async def get_user(self,user_id):

        con=sqlite3.connect(DB_NAME)
        cur=con.cursor()

        cur.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
        )

        row=cur.fetchone()

        con.close()

        return row



    async def activate_plan(self,user_id,plan):

        days=30

        expire=datetime.utcnow()+timedelta(days=days)

        p=PLANS[plan]


        async with self.lock:

            con=sqlite3.connect(DB_NAME)
            cur=con.cursor()


            cur.execute(
            """
            UPDATE users
            SET plan=?,
            spot=?,
            futures=?,
            alerts=?,
            expire=?
            WHERE id=?
            """,
            (
                plan,
                int(p.spot),
                int(p.futures),
                int(p.alerts),
                expire.isoformat(),
                user_id
            )
            )


            con.commit()
            con.close()



    async def has_spot(self,user_id):

        user=await self.get_user(user_id)

        if not user:
            return False

        return bool(user[3])



    async def has_futures(self,user_id):

        user=await self.get_user(user_id)

        if not user:
            return False

        return bool(user[4])



    async def can_receive_alerts(self,user_id):

        user=await self.get_user(user_id)

        if not user:
            return False

        return bool(user[5])



    async def all_alert_users(self):

        con=sqlite3.connect(DB_NAME)
        cur=con.cursor()


        cur.execute(
        """
        SELECT id FROM users
        WHERE alerts=1
        """
        )

        rows=cur.fetchall()

        con.close()

        return [x[0] for x in rows]



    async def save_alert(self,user_id,message):

        async with self.lock:

            con=sqlite3.connect(DB_NAME)
            cur=con.cursor()


            cur.execute(
            """
            INSERT INTO alerts
            (user_id,message,created)
            VALUES(?,?,?)
            """,
            (
                user_id,
                message,
                datetime.utcnow().isoformat()
            )
            )


            con.commit()
            con.close()



    async def save_signal(
        self,
        symbol,
        market,
        action,
        price
    ):

        con=sqlite3.connect(DB_NAME)
        cur=con.cursor()


        cur.execute(
        """
        INSERT INTO signals
        (symbol,market,action,price,created)
        VALUES(?,?,?,?,?)
        """,
        (
            symbol,
            market,
            action,
            price,
            datetime.utcnow().isoformat()
        )
        )


        con.commit()
        con.close()
