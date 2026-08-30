import sqlite3
from datetime import datetime, timedelta

from config import DATABASE, FREE_DAYS


class Database:

    def __init__(self):
        self.conn = sqlite3.connect(
            DATABASE,
            check_same_thread=False
        )

        self.create()


    def create(self):

        cur = self.conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            username TEXT,
            expire TEXT
        )
        """)

        self.conn.commit()


    def add_user(self, user_id, username):

        cur = self.conn.cursor()

        cur.execute(
            "SELECT id FROM users WHERE id=?",
            (user_id,)
        )

        if not cur.fetchone():

            expire = (
                datetime.utcnow()
                +
                timedelta(days=FREE_DAYS)
            ).isoformat()

            cur.execute(
                """
                INSERT INTO users
                VALUES(?,?,?)
                """,
                (
                    user_id,
                    username,
                    expire
                )
            )

            self.conn.commit()



    def active(self,user_id):

        cur=self.conn.cursor()

        cur.execute(
            "SELECT expire FROM users WHERE id=?",
            (user_id,)
        )

        row=cur.fetchone()

        if not row:
            return False


        return datetime.utcnow() < datetime.fromisoformat(row[0])



    def status(self,user_id):

        cur=self.conn.cursor()

        cur.execute(
            "SELECT expire FROM users WHERE id=?",
            (user_id,)
        )

        row=cur.fetchone()

        return row[0] if row else None
