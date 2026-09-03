import aiohttp
import logging


logger = logging.getLogger(__name__)


class CryptoAPI:


    def __init__(self):

        self.binance_url = (
            "https://api.binance.com/api/v3"
        )

        self.coingecko_url = (
            "https://api.coingecko.com/api/v3"
        )



    async def get_klines(
        self,
        symbol,
        interval="4h",
        limit=100
    ):

        """
        جلب شموع Binance
        """

        symbol = symbol.upper() + "USDT"


        url = (
            f"{self.binance_url}/klines"
            f"?symbol={symbol}"
            f"&interval={interval}"
            f"&limit={limit}"
        )


        try:

            async with aiohttp.ClientSession() as session:

                async with session.get(url) as response:


                    data = await response.json()



            candles = []


            for item in data:

    candles.append({

        "time":
            int(item[0]),

        "open":
            float(item[1]),

        "high":
            float(item[2]),

        "low":
            float(item[3]),

        "close":
            float(item[4]),

        "volume":
            float(item[5])

    })



            return candles



        except Exception as e:

            logger.error(
                f"Binance error: {e}"
            )

            return []




    async def get_coin_data(
        self,
        symbol
    ):


        """
        معلومات السعر
        """


        ids = {

            "BTC":
                "bitcoin",

            "ETH":
                "ethereum",

            "BNB":
                "binancecoin",

            "SOL":
                "solana"

        }


        coin_id = ids.get(
            symbol.upper()
        )


        if not coin_id:

            return None



        url = (

            f"{self.coingecko_url}/simple/price"

            f"?ids={coin_id}"

            "&vs_currencies=usd"

            "&include_24hr_change=true"

        )



        try:

            async with aiohttp.ClientSession() as session:

                async with session.get(url) as response:

                    data = await response.json()



            coin = data[coin_id]


            return {

                "name":
                    symbol.upper(),

                "symbol":
                    symbol.upper(),

                "current_price":
                    coin["usd"],

                "price_change_24h":
                    coin.get(
                        "usd_24h_change",
                        0
                    )

            }



        except Exception as e:


            logger.error(
                f"CoinGecko error: {e}"
            )

            return None




    async def get_tvl(
        self,
        symbol
    ):

        """
        نسخة أولية لـ TVL
        لاحقاً تربط مع DeFiLlama
        """


        return {

            "tvl": 0,

            "tvl_change_30d": 0

        }
