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


    # =====================================
    # GET BINANCE CANDLES
    # =====================================

    async def get_klines(
        self,
        symbol,
        interval="4h",
        limit=100
    ):

        symbol = (
            symbol.upper()
            .replace("USDT", "")
            + "USDT"
        )

        url = (
            f"{self.binance_url}/klines"
            f"?symbol={symbol}"
            f"&interval={interval}"
            f"&limit={limit}"
        )

        try:

            async with aiohttp.ClientSession() as session:

                async with session.get(
                    url
                ) as response:

                    if response.status != 200:

                        logger.error(
                            f"Binance status error: "
                            f"{response.status}"
                        )

                        return []

                    data = await response.json()


            if not isinstance(
                data,
                list
            ):

                logger.error(
                    f"Invalid Binance response: {data}"
                )

                return []


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


        except Exception as error:

            logger.exception(
                f"Binance error: {error}"
            )

            return []


    # =====================================
    # GET BASIC COIN DATA
    # =====================================

    async def get_coin_data(
        self,
        symbol
    ):

        symbol = (
            symbol.upper()
            .replace("USDT", "")
            .replace("/", "")
            .strip()
        )


        ids = {

            "BTC":
                "bitcoin",

            "ETH":
                "ethereum",

            "BNB":
                "binancecoin",

            "SOL":
                "solana",

            "AVAX":
                "avalanche-2",

            "MATIC":
                "matic-network",

            "POL":
                "matic-network",

            "ARB":
                "arbitrum",

            "OP":
                "optimism",

            "SEI":
                "sei-network"

        }


        coin_id = ids.get(
            symbol
        )


        if not coin_id:

            logger.warning(
                f"No CoinGecko mapping for {symbol}"
            )

            return None


        url = (

            f"{self.coingecko_url}/simple/price"

            f"?ids={coin_id}"

            "&vs_currencies=usd"

            "&include_24hr_change=true"

        )


        try:

            async with aiohttp.ClientSession() as session:

                async with session.get(
                    url
                ) as response:

                    if response.status != 200:

                        logger.error(
                            f"CoinGecko status error: "
                            f"{response.status}"
                        )

                        return None


                    data = await response.json()


            coin = data.get(
                coin_id
            )


            if not coin:

                return None


            return {

                "name":
                    symbol,

                "symbol":
                    symbol,

                "current_price":
                    coin.get(
                        "usd",
                        0
                    ),

                "price_change_24h":
                    coin.get(
                        "usd_24h_change",
                        0
                    )

            }


        except Exception as error:

            logger.exception(
                f"CoinGecko error: {error}"
            )

            return None


    # =====================================
    # GET TVL DATA
    # =====================================

    async def get_tvl(
        self,
        symbol
    ):

        symbol = (
            symbol.upper()
            .replace("USDT", "")
            .replace("/", "")
            .strip()
        )


        protocols = {

            "ETH":
                "ethereum",

            "SOL":
                "solana",

            "AVAX":
                "avalanche",

            "MATIC":
                "polygon",

            "POL":
                "polygon",

            "ARB":
                "arbitrum",

            "OP":
                "optimism",

            "SEI":
                "sei"

        }


        protocol = protocols.get(
            symbol
        )


        if not protocol:

            logger.warning(
                f"No TVL mapping for {symbol}"
            )

            return None


        url = (

            "https://api.llama.fi/v2/"
            f"historicalChainTvl/{protocol}"

        )


        try:

            async with aiohttp.ClientSession() as session:

                async with session.get(
                    url
                ) as response:


                    if response.status != 200:

                        logger.error(
                            f"DeFiLlama status error: "
                            f"{response.status}"
                        )

                        return None


                    data = await response.json()


            if not data:

                logger.warning(
                    f"No TVL data for {symbol}"
                )

                return None


            tvl_history = []


            for item in data:

                tvl_history.append({

                    "date":
                        item.get("date"),

                    "tvl":
                        float(
                            item.get(
                                "tvl",
                                0
                            )
                        )

                })


            if not tvl_history:

                return None


            current_tvl = (

                tvl_history[-1]
                .get(
                    "tvl",
                    0
                )

            )


            change_30d = 0


            if len(
                tvl_history
            ) >= 30:


                old_tvl = (

                    tvl_history[-30]
                    .get(
                        "tvl",
                        0
                    )

                )


                if old_tvl > 0:


                    change_30d = (

                        (

                            current_tvl
                            -
                            old_tvl

                        )

                        /

                        old_tvl

                    ) * 100


            return {

                "tvl":
                    current_tvl,

                "tvl_change_30d":
                    round(
                        change_30d,
                        2
                    ),

                "history":
                    tvl_history

            }


        except Exception as error:

            logger.exception(
                f"TVL error: {error}"
            )

            return None
