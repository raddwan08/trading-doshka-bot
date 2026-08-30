# market/binance.py

import requests
from datetime import datetime


SPOT_API = "https://api.binance.com/api/v3"
FUTURES_API = "https://fapi.binance.com/fapi/v1"


def normalize_symbol(symbol):
    """
    تحويل BTC/USDT إلى BTCUSDT
    """
    return symbol.replace("/", "").upper()



def get_price(symbol="BTC/USDT"):
    """
    جلب سعر Spot من Binance
    """
    try:
        symbol = normalize_symbol(symbol)

        url = f"{SPOT_API}/ticker/price"

        response = requests.get(
            url,
            params={
                "symbol": symbol
            },
            timeout=10
        )

        data = response.json()

        return float(data["price"])

    except Exception as e:
        print("get_price error:", e)
        return None



def get_futures_price(symbol="BTC/USDT"):
    """
    جلب سعر Futures من Binance
    """
    try:
        symbol = normalize_symbol(symbol)

        url = f"{FUTURES_API}/ticker/price"

        response = requests.get(
            url,
            params={
                "symbol": symbol
            },
            timeout=10
        )

        data = response.json()

        return float(data["price"])

    except Exception as e:
        print("get_futures_price error:", e)
        return None



def get_market_status(symbol="BTC/USDT"):
    """
    حالة السوق
    """
    price = get_price(symbol)

    if price is None:
        return {
            "status": "offline",
            "symbol": symbol
        }


    return {
        "status": "online",
        "exchange": "Binance",
        "market": "Spot",
        "symbol": symbol,
        "price": price,
        "time": datetime.utcnow().isoformat()
    }



def market_status(symbol="BTC/USDT"):
    """
    توافق مع النسخ القديمة
    """
    return get_market_status(symbol)



def get_market_data(
    symbol="BTC/USDT",
    timeframe="1h",
    limit=50
):
    """
    جلب الشموع
    """
    try:
        symbol = normalize_symbol(symbol)

        url = f"{SPOT_API}/klines"

        response = requests.get(
            url,
            params={
                "symbol": symbol,
                "interval": timeframe,
                "limit": limit
            },
            timeout=10
        )

        return response.json()


    except Exception as e:
        print("get_market_data error:", e)
        return []



def get_spot_and_futures(symbol="BTC/USDT"):
    """
    مقارنة Spot و Futures
    """

    return {
        "symbol": symbol,
        "spot": get_price(symbol),
        "futures": get_futures_price(symbol)
    }



def check_connection():
    """
    اختبار اتصال Binance
    """
    try:

        response = requests.get(
            f"{SPOT_API}/ping",
            timeout=5
        )

        return response.status_code == 200

    except:
        return False
