def ema(data, period):

    return data.ewm(
        span=period
    ).mean()



def rsi(data, period=14):

    delta=data.diff()

    gain=delta.where(
        delta>0,
        0
    )

    loss=-delta.where(
        delta<0,
        0
    )


    avg_gain=gain.rolling(
        period
    ).mean()


    avg_loss=loss.rolling(
        period
    ).mean()


    rs=avg_gain/avg_loss


    return 100-(100/(1+rs))



def macd(data):

    fast=ema(
        data,
        12
    )

    slow=ema(
        data,
        26
    )


    return fast-slow
