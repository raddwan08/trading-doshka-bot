import aiohttp


BINANCE_FUTURE = "https://fapi.binance.com"


async def future_price(symbol):

    url = f"{BINANCE_FUTURE}/fapi/v1/ticker/price"

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
                    "type": "FUTURE",
                    "symbol": symbol.upper(),
                    "price": float(data["price"])
                }


    except Exception as e:

        return {
            "type": "FUTURE",
            "error": str(e)
        }



async def future_signal(symbol):

    price = await future_price(symbol)


    return {

        "market": "Future",
        "signal": "WAIT",
        "subscription": "PREMIUM",
        "data": price

    }



async def check_contract(symbol):

    """
    فحص حالة عقد العملة
    """

    url = f"{BINANCE_FUTURE}/fapi/v1/exchangeInfo"


    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(url) as response:

                data = await response.json()


                for item in data["symbols"]:

                    if item["symbol"] == symbol.upper():

                        return {

                            "symbol": symbol.upper(),
                            "status": item["status"],
                            "contract": item["contractType"]

                        }


        return None


    except Exception as e:

        return {

            "error": str(e)

        }
