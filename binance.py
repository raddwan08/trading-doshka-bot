
import aiohttp
import time


BINANCE_API = "https://api.binance.com"


async def get_price(symbol: str):
    """
    جلب السعر الحالي للعملة
    مثال:
    BTCUSDT
    ETHUSDT
    """

    symbol = symbol.upper()

    url = f"{BINANCE_API}/api/v3/ticker/price"

    params = {
        "symbol": symbol
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=10
            ) as response:

                data = await response.json()

                if "price" in data:
                    return float(data["price"])

                return None

    except Exception as e:
        print("BINANCE PRICE ERROR:", e)
        return None



async def get_candles(
    symbol="BTCUSDT",
    interval="1h",
    limit=100
):
    """
    جلب الشموع للتحليل الفني
    """

    url = f"{BINANCE_API}/api/v3/klines"

    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit
    }


    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                url,
                params=params,
                timeout=10
            ) as response:

                data = await response.json()


                candles = []


                for candle in data:

                    candles.append(
                        {
                            "time": candle[0],
                            "open": float(candle[1]),
                            "high": float(candle[2]),
                            "low": float(candle[3]),
                            "close": float(candle[4]),
                            "volume": float(candle[5])
                        }
                    )


                return candles


    except Exception as e:

        print("BINANCE CANDLE ERROR:", e)
        return []



async def market_status(symbol):

    """
    حالة السوق
    """

    price = await get_price(symbol)

    if not price:
        return {
            "status": "error",
            "message": "لا يوجد بيانات"
        }


    return {

        "symbol": symbol.upper(),
        "price": price,
        "time": int(time.time())

    }
