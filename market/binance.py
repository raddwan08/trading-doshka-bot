
import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")


exchange = ccxt.binance({
    "apiKey": API_KEY,
    "secret": SECRET_KEY,
    "enableRateLimit": True,
})


def get_price(symbol="BTC/USDT"):
    try:
        ticker = exchange.fetch_ticker(symbol)
        return ticker["last"]
    except Exception as e:
        return None


def get_spot_balance(asset="USDT"):
    try:
        balance = exchange.fetch_balance()
        return balance["free"].get(asset, 0)
    except Exception:
        return 0


def get_market_data(symbol="BTC/USDT", timeframe="1h", limit=100):
    try:
        candles = exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            limit=limit
        )

        return candles

    except Exception:
        return []


def get_signal(symbol="BTC/USDT"):

    price = get_price(symbol)

    if price is None:
        return {
            "signal": "ERROR",
            "price": None
        }

    return {
        "symbol": symbol,
        "price": price,
        "signal": "WATCH"
    }


def get_futures_price(symbol="BTC/USDT"):
    try:
        futures = ccxt.binance({
            "options": {
                "defaultType": "future"
            }
        })

        ticker = futures.fetch_ticker(symbol)

        return ticker["last"]

    except Exception:
        return None
        def get_market_status(symbol="BTC/USDT"):
    try:
        price = get_price(symbol)

        if price:
            return {
                "status": "OPEN",
                "symbol": symbol,
                "price": price
            }

        return {
            "status": "ERROR",
            "symbol": symbol
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "message": str(e)
        }
