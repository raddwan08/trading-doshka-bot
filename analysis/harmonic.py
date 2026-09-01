import math


def fibonacci_ratio(a, b, c):
    """
    حساب نسبة التصحيح
    """
    if b == a:
        return 0

    return abs((c - b) / (b - a))



def analyze(candles):

    if len(candles) < 30:

        return {
            "signal": "WAIT",
            "message": "بيانات غير كافية لنموذج هارمونيك"
        }


    highs = [
        float(x["high"])
        for x in candles
    ]

    lows = [
        float(x["low"])
        for x in candles
    ]


    # آخر أربع نقاط سعرية
    X = lows[-30]
    A = highs[-20]
    B = lows[-10]
    C = highs[-5]
    D = lows[-1]


    AB_XA = fibonacci_ratio(
        X,
        A,
        B
    )


    BC_AB = fibonacci_ratio(
        A,
        B,
        C
    )


    CD_BC = fibonacci_ratio(
        B,
        C,
        D
    )



    pattern = None
    signal = "WAIT"


    # Gartley
    if (
        0.55 <= AB_XA <= 0.65
        and
        0.35 <= BC_AB <= 0.90
        and
        1.20 <= CD_BC <= 1.70
    ):

        pattern = "Gartley"
        signal = "BUY"



    # Butterfly
    elif (
        0.75 <= AB_XA <= 0.85
        and
        1.50 <= CD_BC <= 2.00
    ):

        pattern = "Butterfly"
        signal = "BUY"



    # Bat
    elif (
        0.35 <= AB_XA <= 0.55
        and
        1.50 <= CD_BC <= 2.60
    ):

        pattern = "Bat"
        signal = "BUY"



    # Crab
    elif (
        0.35 <= AB_XA <= 0.65
        and
        CD_BC >= 2.50
    ):

        pattern = "Crab"
        signal = "BUY"



    if pattern:

        message = (
            f"🦋 نموذج هارمونيك مكتشف\n\n"
            f"النموذج: {pattern}\n"
            f"الإشارة: {signal}\n"
            f"تم الوصول لمنطقة انعكاس محتملة"
        )

    else:

        message = (
            "🦋 لا يوجد نموذج هارمونيك واضح حالياً\n"
            "انتظار تشكل نموذج جديد"
        )



    return {

        "school": "Harmonic",

        "pattern": pattern,

        "signal": signal,

        "message": message,

        "ratios": {

            "AB_XA": round(
                AB_XA,
                2
            ),

            "BC_AB": round(
                BC_AB,
                2
            ),

            "CD_BC": round(
                CD_BC,
                2
            )
        }

    }
