import aiohttp

BINANCE_SPOT = "https://api.binance.com"


async def spot_price(symbol):

    url = f"{BINANCE_SPOT}/api/v3/ticker/price"

    params = {
        "symbol": symbol.upper()
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params
            ) as response:

                data = await response.json()

                return {
                    "type": "SPOT",
                    "symbol": symbol.upper(),
                    "price": float(data["price"])
                }

    except Exception as e:

        return {
            "type": "SPOT",
            "error": str(e)
        }


async def spot_signal(symbol):

    price = await spot_price(symbol)

    return {
        "market": "Spot",
        "signal": "WAIT",
        "data": price
    }
