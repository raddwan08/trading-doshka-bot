import numpy as np


SCHOOL_NAME = "📉 التحليل الكلاسيكي"

REQUIRES_CANDLES = True


# =====================================
# RSI
# =====================================

def calculate_rsi(
    closes,
    period=14
):

    closes = np.array(
        closes,
        dtype=float
    )

    if len(closes) < period + 1:

        return 50.0


    deltas = np.diff(
        closes
    )


    gains = np.where(
        deltas > 0,
        deltas,
        0
    )


    losses = np.where(
        deltas < 0,
        -deltas,
        0
    )


    avg_gain = np.mean(
        gains[-period:]
    )


    avg_loss = np.mean(
        losses[-period:]
    )


    if avg_loss == 0:

        return 100.0


    rs = avg_gain / avg_loss


    rsi = 100 - (
        100 / (1 + rs)
    )


    return float(
        rsi
    )


# =====================================
# EMA SERIES
# =====================================

def calculate_ema(
    values,
    period
):

    values = np.array(
        values,
        dtype=float
    )


    if len(values) == 0:

        return []


    ema_values = []

    multiplier = (
        2 / (period + 1)
    )


    current_ema = values[0]

    ema_values.append(
        float(current_ema)
    )


    for price in values[1:]:

        current_ema = (

            (
                price -
                current_ema
            )

            * multiplier

            +

            current_ema

        )


        ema_values.append(
            float(current_ema)
        )


    return ema_values


# =====================================
# SUPPORT / RESISTANCE
# =====================================

def find_support_resistance(
    highs,
    lows,
    period=20
):

    recent_highs = (
        highs[-period:]
    )


    recent_lows = (
        lows[-period:]
    )


    support = min(
        recent_lows
    )


    resistance = max(
        recent_highs
    )


    return (

        float(support),

        float(resistance)

    )


# =====================================
# MAIN ANALYSIS
# =====================================

def analyze(
    candles
):

    if not candles or len(candles) < 50:

        return {

            "school": "Classic",

            "signal": "WAIT",

            "message": (
                "بيانات غير كافية "
                "لإجراء التحليل الكلاسيكي."
            )

        }


    closes = np.array(

        [

            float(
                candle["close"]
            )

            for candle in candles

        ]

    )


    highs = np.array(

        [

            float(
                candle["high"]
            )

            for candle in candles

        ]

    )


    lows = np.array(

        [

            float(
                candle["low"]
            )

            for candle in candles

        ]

    )


    # =================================
    # INDICATORS
    # =================================

    rsi = calculate_rsi(
        closes
    )


    ema20_series = calculate_ema(
        closes,
        20
    )


    ema50_series = calculate_ema(
        closes,
        50
    )


    ema20 = ema20_series[-1]

    ema50 = ema50_series[-1]


    current_price = float(
        closes[-1]
    )


    support, resistance = (
        find_support_resistance(

            highs,

            lows

        )
    )


    # =================================
    # SCORE
    # =================================

    score = 0


    # RSI

    if rsi < 30:

        score += 2


    elif rsi > 70:

        score -= 2


    # EMA TREND

    if ema20 > ema50:

        score += 2


    else:

        score -= 2


    # PRICE POSITION

    if current_price > ema20:

        score += 1


    else:

        score -= 1


    # =================================
    # SIGNAL
    # =================================

    target = None

    stop_loss = None


    if score >= 3:

        signal = "BUY"


        message = (

            "📈 الاتجاه العام صاعد.\n"
            "📊 السعر أعلى المتوسطات المتحركة.\n"
            "🚀 المؤشرات تدعم احتمالية الشراء."

        )


        target = resistance


        stop_loss = support


    elif score <= -3:

        signal = "SELL"


        message = (

            "📉 الاتجاه العام هابط.\n"
            "📊 السعر تحت المتوسطات المتحركة.\n"
            "⚠️ ضغط البيع واضح."

        )


        target = support


        stop_loss = resistance


    else:

        signal = "WAIT"


        message = (

            "📊 السوق في حالة تذبذب.\n"
            "⚖️ لا توجد إشارة قوية حالياً."

        )


    # =================================
    # RESULT
    # =================================

    return {

        "school": "Classic",

        "signal": signal,

        "message": message,

        "rsi": round(
            rsi,
            2
        ),

        "ema20": round(
            ema20,
            8
        ),

        "ema50": round(
            ema50,
            8
        ),

        "support": round(
            support,
            8
        ),

        "resistance": round(
            resistance,
            8
        ),

        "target": target,

        "stop_loss": stop_loss,


        "chart": {

            "lines": [

                {

                    "values":
                        ema20_series,

                    "label":
                        "EMA 20",

                    "width":
                        1.5

                },

                {

                    "values":
                        ema50_series,

                    "label":
                        "EMA 50",

                    "width":
                        1.5

                }

            ],


            "levels": [

                {

                    "price":
                        support,

                    "label":
                        "Support",

                    "style":
                        "--"

                },

                {

                    "price":
                        resistance,

                    "label":
                        "Resistance",

                    "style":
                        "--"

                }

            ]

        }

    }
