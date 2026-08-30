# binance.py

import aiohttp
import time

from config import BINANCE_API



# ==========================
# جلب شموع Spot
# ==========================

async def get_spot_klines(
        symbol,
        timeframe="1h",
        limit=200
):

    symbol = symbol.upper()+"USDT"


    url = (
        f"{BINANCE_API}/api/v3/klines"
        f"?symbol={symbol}"
        f"&interval={timeframe}"
        f"&limit={limit}"
    )


    return await fetch_klines(url)



# ==========================
# جلب شموع Futures
# ==========================

async def get_futures_klines(
        symbol,
        timeframe="1h",
        limit=200
):


    symbol=symbol.upper()+"USDT"


    url=(
        "https://fapi.binance.com/fapi/v1/klines"
        f"?symbol={symbol}"
        f"&interval={timeframe}"
        f"&limit={limit}"
    )


    return await fetch_klines(url)




# ==========================
# المعالجة العامة
# ==========================

async def fetch_klines(url):

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                url,
                timeout=15
            ) as response:


                data=await response.json()



                if not isinstance(data,list):

                    return []



                candles=[]



                for x in data:


                    candles.append({

                        "time":
                        x[0],


                        "open":
                        float(x[1]),


                        "high":
                        float(x[2]),


                        "low":
                        float(x[3]),


                        "close":
                        float(x[4]),


                        "volume":
                        float(x[5])

                    })



                return candles



    except Exception as e:

        print(
            "Binance Error:",
            e
        )

        return []




# ==========================
# السعر الحالي
# ==========================

async def current_price(symbol):


    symbol=symbol.upper()+"USDT"


    url=(
        f"{BINANCE_API}/api/v3/ticker/price"
        f"?symbol={symbol}"
    )


    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(url) as r:

                data=await r.json()

                return float(
                    data["price"]
                )


    except:

        return None
