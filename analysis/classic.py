import pandas as pd


def classic_analysis(df, symbol):


    close=df["close"]


    ema20 = (
        close
        .ewm(span=20)
        .mean()
        .iloc[-1]
    )


    price=close.iloc[-1]


    if price > ema20:

        trend="Bullish"

        signal="شراء محتمل"

    else:

        trend="Bearish"

        signal="بيع محتمل"



    return {


"text":f"""
📈 Classic Technical Analysis


{symbol}USDT


Trend:
{trend}


Signal:
{signal}


Indicators:

EMA20:
{ema20:.4f}


Price:
{price:.4f}


Used:
- EMA
- Support Resistance
- Momentum


""",

"entry":[price],

"levels":[ema20,price]

}
