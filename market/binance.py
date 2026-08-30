import requests
import pandas as pd


SPOT_URL = "https://api.binance.com/api/v3"
FUTURES_URL = "https://fapi.binance.com/fapi/v1"



def normalize(symbol):

    symbol = symbol.upper()
    symbol = symbol.replace("/", "")

    if not symbol.endswith("USDT"):
        symbol += "USDT"

    return symbol



def get_price(symbol="BTCUSDT"):

    try:

        symbol = normalize(symbol)

        r = requests.get(
            f"{SPOT_URL}/ticker/price",
            params={
                "symbol": symbol
            },
            timeout=10
        )

        return float(
            r.json()["price"]
        )

    except:

        return None



def get_futures_price(symbol="BTCUSDT"):

    try:

        symbol = normalize(symbol)

        r=requests.get(
            f"{FUTURES_URL}/ticker/price",
            params={
                "symbol":symbol
            },
            timeout=10
        )

        return float(
            r.json()["price"]
        )

    except:

        return None



def get_market_data(
        symbol="BTCUSDT",
        interval="1h",
        limit=200
):

    try:

        symbol=normalize(symbol)

        r=requests.get(

            f"{SPOT_URL}/klines",

            params={

                "symbol":symbol,
                "interval":interval,
                "limit":limit

            },

            timeout=10
        )


        data=r.json()


        df=pd.DataFrame(

            data,

            columns=[

                "time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "q",
                "trades",
                "buy",
                "buy_q",
                "ignore"

            ]

        )


        for c in [
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]:

            df[c]=df[c].astype(float)


        return df


    except:

        return pd.DataFrame()
