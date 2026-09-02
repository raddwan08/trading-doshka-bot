# services/payment_monitor.py

import asyncio
import logging

from datetime import datetime


logger = logging.getLogger(__name__)



# =====================================
# خطط الاشتراك
# =====================================

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



# =====================================
# تفعيل الاشتراك
# =====================================

async def confirm_payment(
    db,
    user_id,
    username,
    plan
):

    data = PLANS.get(plan)


    if not data:

        logger.error(
            "Unknown plan"
        )

        return False



    db.activate_subscription(

        user_id=user_id,

        username=username,

        plan=plan,

        days=data["days"]

    )


    logger.info(
        f"Subscription activated: {user_id}"
    )


    return True




# =====================================
# فحص USDT Solana
# =====================================

async def check_solana_usdt(
    db
):

    """
    سيتم ربطه مع Solana RPC
    لفحص USDT SPL
    """

    pass



# =====================================
# فحص USDT Ethereum
# =====================================

async def check_ethereum_usdt(
    db
):

    """
    سيتم ربطه مع Ethereum RPC
    لفحص USDT ERC20
    """

    pass



# =====================================
# فحص USDT BSC
# =====================================

async def check_bsc_usdt(
    db
):

    """
    سيتم ربطه مع BSC RPC
    لفحص USDT BEP20
    """

    pass




# =====================================
# مراقب الدفع
# =====================================

async def payment_monitor(
    db
):

    logger.info(
        "💳 Payment Monitor Started"
    )


    while True:

        try:

            await check_solana_usdt(
                db
            )


            await check_ethereum_usdt(
                db
            )


            await check_bsc_usdt(
                db
            )


        except Exception as e:

            logger.exception(
                f"Payment monitor error: {e}"
            )


        await asyncio.sleep(
            30
        )
