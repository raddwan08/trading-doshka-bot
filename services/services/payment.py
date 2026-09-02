# services/payment.py

import os
import logging
import aiohttp

from datetime import datetime


logger = logging.getLogger(__name__)


TRON_API_URL = "https://api.trongrid.io/v1/accounts"


# خطط الاشتراك
PLANS = {

    "subscribe_1m": {
        "days": 30,
        "amount": 20
    },

    "subscribe_3m": {
        "days": 90,
        "amount": 50
    },

    "subscribe_6m": {
        "days": 180,
        "amount": 75
    },

    "subscribe_1y": {
        "days": 365,
        "amount": 125
    }

}


class PaymentService:


    def __init__(self, db):

        self.db = db

        self.wallet = os.getenv(
            "TRON_WALLET"
        )

        self.api_key = os.getenv(
            "TRON_API_KEY"
        )


        if not self.wallet:

            raise RuntimeError(
                "TRON_WALLET missing"
            )


        if not self.api_key:

            raise RuntimeError(
                "TRON_API_KEY missing"
            )



    # =================================
    # مراقبة المدفوعات
    # =================================


    async def check_payments(
        self,
        context
    ):


        try:

            payments = self.db.get_pending_payments()


            if not payments:

                return



            transactions = await self.get_transactions()



            for payment in payments:


                payment_id = payment[0]

                user_id = payment[1]

                username = payment[2]

                plan = payment[3]

                amount_required = payment[4]



                for tx in transactions:


                    tx_hash = tx.get(
                        "transaction_id"
                    )


                    if not tx_hash:

                        continue



                    # منع تكرار المعاملة

                    if self.db.transaction_exists(
                        tx_hash
                    ):

                        continue



                    amount = self.get_amount(
                        tx
                    )


                    if amount is None:

                        continue



                    # تحقق من المبلغ

                    if amount >= amount_required:


                        self.db.confirm_payment(

                            payment_id,

                            tx_hash

                        )


                        days = PLANS.get(
                            plan,
                            {}
                        ).get(
                            "days",
                            30
                        )



                        self.db.activate_subscription(

                            user_id,

                            username,

                            plan,

                            days

                        )



                        logger.info(

                            f"Subscription activated {user_id}"

                        )



                        break



        except Exception as e:


            logger.exception(

                f"Payment checker error: {e}"

            )



    # =================================
    # جلب معاملات المحفظة
    # =================================


    async def get_transactions(
        self
    ):


        url = (

            f"{TRON_API_URL}/"
            f"{self.wallet}/transactions/trc20"

        )


        headers = {

            "TRON-PRO-API-KEY":
            self.api_key

        }



        params = {

            "limit": 50,

            "contract_address":
            "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj"

        }



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



    # =================================
    # استخراج قيمة USDT
    # =================================


    def get_amount(
        self,
        tx
    ):


        try:


            value = tx["value"]


            decimals = tx["token_info"]["decimals"]


            amount = (

                int(value)

                /

                (10 ** decimals)

            )


            return amount



        except Exception:


            return None
