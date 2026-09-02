# database/db.py

import sqlite3
import os

from datetime import datetime, timedelta



class Database:


    def __init__(
        self,
        path="data/subscriptions.db"
    ):

        self.path = path

        os.makedirs(
            "data",
            exist_ok=True
        )

        self.init_db()



    # =========================
    # CONNECTION
    # =========================


    def connect(self):

        return sqlite3.connect(
            self.path
        )



    # =========================
    # CREATE TABLES
    # =========================


    def init_db(self):

        conn = self.connect()

        cursor = conn.cursor()



        # USERS

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users
            (

                user_id INTEGER PRIMARY KEY,

                username TEXT,

                plan TEXT,

                expire_date TEXT,

                is_active INTEGER DEFAULT 0

            )
            """
        )



        # PAYMENTS

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS payments
            (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER,

                username TEXT,

                plan TEXT,

                amount REAL,

                currency TEXT,

                network TEXT,

                wallet TEXT,

                tx_hash TEXT UNIQUE,

                status TEXT DEFAULT 'pending',

                created_at TEXT

            )
            """
        )



        conn.commit()

        conn.close()



    # =========================
    # CREATE PAYMENT REQUEST
    # =========================


    def create_payment(

        self,

        user_id,

        username,

        plan,

        amount,

        currency,

        wallet

    ):


        conn = self.connect()

        cursor = conn.cursor()



        cursor.execute(

            """
            INSERT INTO payments

            (
                user_id,
                username,
                plan,
                amount,
                currency,
                network,
                wallet,
                status,
                created_at
            )

            VALUES
            (?,?,?,?,?,?,?,?,?)

            """,

            (

                user_id,

                username,

                plan,

                amount,

                currency,

                "TRC20",

                wallet,

                "pending",

                datetime.now().isoformat()

            )

        )



        payment_id = cursor.lastrowid



        conn.commit()

        conn.close()



        return payment_id



    # =========================
    # GET PENDING PAYMENTS
    # =========================


    def get_pending_payments(self):


        conn = self.connect()

        cursor = conn.cursor()



        cursor.execute(

            """
            SELECT

            id,
            user_id,
            username,
            plan,
            amount

            FROM payments

            WHERE status='pending'

            """

        )


        rows = cursor.fetchall()



        conn.close()


        return rows



    # =========================
    # CHECK TX EXISTS
    # =========================


    def transaction_exists(

        self,

        tx_hash

    ):


        conn = self.connect()

        cursor = conn.cursor()



        cursor.execute(

            """
            SELECT id

            FROM payments

            WHERE tx_hash=?

            """,

            (
                tx_hash,
            )

        )



        result = cursor.fetchone()



        conn.close()



        return result is not None



    # =========================
    # CONFIRM PAYMENT
    # =========================


    def confirm_payment(

        self,

        payment_id,

        tx_hash

    ):


        conn = self.connect()

        cursor = conn.cursor()



        cursor.execute(

            """
            UPDATE payments

            SET

            status='confirmed',

            tx_hash=?

            WHERE id=?

            """,

            (

                tx_hash,

                payment_id

            )

        )



        conn.commit()

        conn.close()



    # =========================
    # ACTIVATE SUBSCRIPTION
    # =========================


    def activate_subscription(

        self,

        user_id,

        username,

        plan,

        days

    ):


        expire = (

            datetime.now()

            +

            timedelta(
                days=days
            )

        )



        conn = self.connect()

        cursor = conn.cursor()



        cursor.execute(

            """

            INSERT INTO users

            (

            user_id,

            username,

            plan,

            expire_date,

            is_active

            )


            VALUES

            (?,?,?,?,1)


            ON CONFLICT(user_id)

            DO UPDATE SET


            username=excluded.username,

            plan=excluded.plan,

            expire_date=excluded.expire_date,

            is_active=1


            """,

            (

                user_id,

                username,

                plan,

                expire.strftime(
                    "%Y-%m-%d"
                )

            )

        )



        conn.commit()

        conn.close()



    # =========================
    # CHECK SUBSCRIPTION
    # =========================


    def check_subscription(

        self,

        user_id

    ):


        conn = self.connect()

        cursor = conn.cursor()



        cursor.execute(

            """

            SELECT

            expire_date,

            is_active


            FROM users


            WHERE user_id=?


            """,

            (

                user_id,

            )

        )



        row = cursor.fetchone()



        conn.close()



        if not row:

            return False



        expire_date, active = row



        if active != 1:

            return False



        try:

            expire = datetime.strptime(

                expire_date,

                "%Y-%m-%d"

            )


            return expire >= datetime.now()



        except:


            return False
