import numpy as np


def analyze(candles):
    """
    تحليل وايكوف
    candles:
    [
      {
        open,
        high,
        low,
        close,
        volume
      }
    ]
    """

    if len(candles) < 20:
        return {
            "signal": "WAIT",
            "message": "بيانات غير كافية"
        }


    closes = np.array(
        [float(x["close"]) for x in candles]
    )

    volumes = np.array(
        [float(x["volume"]) for x in candles]
    )


    current_price = closes[-1]


    avg_volume = np.mean(
        volumes[-20:]
    )


    current_volume = volumes[-1]


    price_change = (
        (closes[-1] - closes[-20])
        /
        closes[-20]
    ) * 100



    # اكتشاف زيادة الحجم مع صعود السعر
    if (
        current_volume > avg_volume * 1.5
        and price_change > 3
    ):

        signal = "STRONG_BUY"

        message = (
            "📈 مرحلة تجميع وايكوف\n"
            "زيادة حجم مع صعود السعر\n"
            "احتمال استمرار الاتجاه الصاعد"
        )


    elif (
        current_volume > avg_volume * 1.5
        and price_change < -3
    ):

        signal = "STRONG_SELL"

        message = (
            "📉 مرحلة توزيع وايكوف\n"
            "ضغط بيع قوي"
        )


    elif price_change > 1:

        signal = "BUY"

        message = (
            "📊 ميل إيجابي حسب وايكوف"
        )


    elif price_change < -1:

        signal = "SELL"

        message = (
            "📊 ميل سلبي حسب وايكوف"
        )


    else:

        signal = "WAIT"

        message = (
            "⏳ السوق في حالة انتظار"
        )


    return {

        "school": "Wyckoff",

        "signal": signal,

        "price_change": round(
            price_change,
            2
        ),

        "message": message
    }
