import sqlite3
import os
from datetime import datetime, timedelta


class Database:


    def __init__(self, path="data/subscriptions.db"):

        self.path = path

        os.makedirs(
            "data",
            exist_ok=True
        )

        self.init_db()



    def connect(self):

        return sqlite3.connect(
            self.path
        )



    def init_db(self):

        conn = self.connect()

        cursor = conn.cursor()


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


        conn.commit()

        conn.close()



    def check_subscription(
        self,
        user_id
    ):


        conn = self.connect()

        cursor = conn.cursor()


        cursor.execute(

            """
            SELECT expire_date,is_active
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


            if expire < datetime.now():

                return False


            return True


        except:


            return False




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
            timedelta(days=days)
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
