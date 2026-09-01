import numpy as np


def calculate_rsi(closes, period=14):

    if len(closes) < period + 1:
        return 50


    deltas = np.diff(closes)

    gains = []
    losses = []


    for d in deltas:

        if d >= 0:
            gains.append(d)
            losses.append(0)

        else:
            gains.append(0)
            losses.append(abs(d))


    avg_gain = np.mean(
        gains[-period:]
    )

    avg_loss = np.mean(
        losses[-period:]
    )


    if avg_loss == 0:
        return 100


    rs = avg_gain / avg_loss

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi



def ema(values, period):

    if len(values) < period:
        return values[-1]


    return np.mean(
        values[-period:]
    )



def find_support_resistance(
    highs,
    lows
):

    resistance = max(
        highs[-20:]
    )

    support = min(
        lows[-20:]
    )


    return support, resistance



def analyze(candles):


    if len(candles) < 50:

        return {
            "signal": "WAIT",
            "message": "بيانات غير كافية"
        }



    closes = np.array(
        [
            float(x["close"])
            for x in candles
        ]
    )


    highs = [
        float(x["high"])
        for x in candles
    ]


    lows = [
        float(x["low"])
        for x in candles
    ]



    current = closes[-1]


    rsi = calculate_rsi(
        closes
    )


    ema20 = ema(
        closes,
        20
    )

    ema50 = ema(
        closes,
        50
    )


    support, resistance = (
        find_support_resistance(
            highs,
            lows
        )
    )



    score = 0



    # RSI

    if rsi < 30:

        score += 2

    elif rsi > 70:

        score -= 2



    # EMA trend

    if ema20 > ema50:

        score += 2

    else:

        score -= 2



    # Price location

    if current > ema20:

        score += 1

    else:

        score -= 1




    if score >= 3:

        signal = "BUY"
        message = (
            "📈 الاتجاه صاعد\n"
            "RSI و EMA يدعمان الشراء"
        )


    elif score <= -3:

        signal = "SELL"

        message = (
            "📉 الاتجاه هابط\n"
            "ضغط بيع واضح"
        )


    else:

        signal = "WAIT"

        message = (
            "📊 لا توجد إشارة قوية"
        )



    return {

        "school": "Classic",

        "signal": signal,

        "rsi": round(
            rsi,
            2
        ),

        "ema20": round(
            ema20,
            4
        ),

        "ema50": round(
            ema50,
            4
        ),

        "support": round(
            support,
            4
        ),

        "resistance": round(
            resistance,
            4
        ),

        "message": message

    }
