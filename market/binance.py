import aiohttp
import asyncio
from datetime import datetime


BINANCE_SPOT = "https://api.binance.com"
BINANCE_FUTURES = "https://fapi.binance.com"


async def get_price(symbol="BTCUSDT", market="spot"):
    """
    جلب السعر الحالي
    """
    base = BINANCE_SPOT if market == "spot" else BINANCE_FUTURES

    url = f"{base}/api/v3/ticker/price"

    if market == "futures":
        url = f"{base}/fapi/v1/ticker/price"

    params = {
        "symbol": symbol.upper()
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()

            return {
                "symbol": symbol.upper(),
                "price": float(data["price"]),
                "market": market,
                "time": datetime.utcnow().isoformat()
            }


async def get_candles(symbol="BTCUSDT", interval="1h", limit=100, market="spot"):
    """
    جلب الشموع للتحليل الفني
    """

    if market == "spot":
        url = f"{BINANCE_SPOT}/api/v3/klines"
    else:
        url = f"{BINANCE_FUTURES}/fapi/v1/klines"


    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit
    }


    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:

            candles = await response.json()

            result = []

            for c in candles:
                result.append({

                    "time": datetime.fromtimestamp(
                        c[0] / 1000
                    ).isoformat(),

                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5])

                })

            return result



async def get_market_data(symbol, interval="1h", market="spot"):

    price = await get_price(
        symbol,
        market
    )

    candles = await get_candles(
        symbol,
        interval,
        100,
        market
    )


    return {

        "info": price,

        "candles": candles

    }



# اختبار مباشر
if __name__ == "__main__":

    async def test():

        data = await get_market_data(
            "BTCUSDT",
            "1h",
            "spot"
        )

        print(data["info"])
        print(
            len(data["candles"]),
            "candles loaded"
        )


    asyncio.run(test())
