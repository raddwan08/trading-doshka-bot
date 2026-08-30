import time


subscribers = []


def add_subscriber(user_id):

    if user_id not in subscribers:
        subscribers.append(user_id)


def remove_subscriber(user_id):

    if user_id in subscribers:
        subscribers.remove(user_id)



def create_alert(
    symbol,
    action,
    price,
    market="SPOT"
):

    return {

        "symbol": symbol.upper(),

        "market": market,

        "action": action,

        "price": price,

        "time": time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    }



async def send_alerts(bot, alert):

    message = f"""
🚨 تنبيه تداول

العملة:
{alert['symbol']}

السوق:
{alert['market']}

الحالة:
{alert['action']}

السعر:
{alert['price']}

الوقت:
{alert['time']}
"""


    for user in subscribers:

        try:

            await bot.send_message(
                user,
                message
            )

        except Exception as e:

            print(
                "Alert error:",
                e
            )
