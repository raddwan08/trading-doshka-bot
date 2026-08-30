from market.binance import get_market_data,get_price,get_futures_price
from market.indicators import ema,rsi,macd



def analyze_market(symbol):


    df=get_market_data(
        symbol
    )


    price=get_price(
        symbol
    )


    futures=get_futures_price(
        symbol
    )


    if df.empty:

        return {

            "price":price,
            "trend":"غير معروف",
            "signal":"لا توجد بيانات",
            "strength":0,
            "support":0,
            "resistance":0,
            "market":"ERROR"

        }



    close=df["close"]



    e20=ema(
        close,
        20
    )


    r=rsi(
        close
    ).iloc[-1]


    m=macd(
        close
    ).iloc[-1]



    trend="جانبي"
    signal="انتظار"
    strength=50



    if close.iloc[-1] > e20.iloc[-1]:

        trend="صاعد"

        signal="شراء محتمل"

        strength+=20


    else:

        trend="هابط"

        signal="بيع محتمل"

        strength-=10



    if r < 30:

        signal="شراء قوي"

        strength+=20


    if r > 70:

        signal="بيع"

        strength-=20



    return {


        "price":price,

        "trend":trend,

        "signal":signal,

        "strength":max(
            0,
            min(
                strength,
                100
            )
        ),


        "support":float(
            df["low"].tail(50).min()
        ),


        "resistance":float(
            df["high"].tail(50).max()
        ),


        "market":

        f"Spot: {price} | Futures: {futures}"

    }
