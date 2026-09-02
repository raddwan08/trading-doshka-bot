# services/payment.py

import os
import logging
import aiohttp

from datetime import datetime


logger = logging.getLogger(__name__)


# عقد USDT على شبكة Tron TRC20
USDT_CONTRACT = (
    "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj"
)


TRON_API = (
    "https://api.trongrid.io"
)



class PaymentService:


    def __init__(
        self,
        db
    ):

        self.db = db

        self.wallet = os.getenv(
            "TRON_WALLET"
        )

        self.api_key = os.getenv(
            "TRON_API_KEY"
        )


        if not self.wallet:

            logger.warning(
                "TRON_WALLET is not set"
            )



    # =================================
    # جلب معاملات USDT
    # =================================

    async def get_transactions(
        self
    ):

        if not self.wallet:

            return []


        url = (
            f"{TRON_API}/v1/accounts/"
            f"{self.wallet}/transactions/trc20"
        )


        headers = {}


        if self.api_key:

            headers["TRON-PRO-API-KEY"] = (
                self.api_key
            )


        params = {

            "contract_address":
                USDT_CONTRACT,

            "limit": 20,

            "only_confirmed":
                "true"

        }


        try:

            async with aiohttp.ClientSession() as session:

                async with session.get(
                    url,
                    headers=headers,
                    params=params
                ) as response:


                    data = await response.json()


                    return data.get(
                        "data",
                        []
                    )


        except Exception as e:

            logger.error(
                f"TRON API error: {e}"
            )

            return []



    # =================================
    # فحص الدفعات
    # =================================

    async def check_payments(
        self
    ):


        transactions = await (
            self.get_transactions()
        )


        if not transactions:

            return



        pending = (
            self.db.get_pending_payments()
        )


        for tx in transactions:


            tx_hash = tx.get(
                "transaction_id"
            )


            if not tx_hash:

                continue



            value = (
                int(
                    tx["value"]
                )
                /
                1000000
            )


            receiver = tx.get(
                "to"
            )


            for payment in pending:


                payment_id = payment[0]

                user_id = payment[1]

                username = payment[2]

                plan = payment[3]

                amount = payment[4]



                if receiver != self.wallet:

                    continue



                if abs(
                    value - amount
                ) > 0.01:

                    continue



                # تأكيد الدفع

                self.db.confirm_payment(
                    payment_id,
                    tx_hash
                )


                # تفعيل الاشتراك

                days = {

                    "subscribe_1m":30,

                    "subscribe_3m":90,

                    "subscribe_6m":180,

                    "subscribe_1y":365

                }.get(
                    plan
                )


                if days:


                    self.db.activate_subscription(

                        user_id,

                        username,

                        plan,

                        days

                    )


                    logger.info(

                        f"Activated {user_id}"

                    )
