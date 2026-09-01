import numpy as np


def analyze(candles):

    if len(candles) < 30:

        return {
            "signal": "WAIT",
            "message": "بيانات غير كافية لتحليل الحيتان"
        }



    closes = np.array(
        [
            float(x["close"])
            for x in candles
        ]
    )


    volumes = np.array(
        [
            float(x["volume"])
            for x in candles
        ]
    )



    current_volume = volumes[-1]


    average_volume = np.mean(
        volumes[-30:]
    )


    volume_ratio = (
        current_volume /
        average_volume
        if average_volume > 0
        else 1
    )



    price_change = (
        (
            closes[-1]
            -
            closes[-10]
        )
        /
        closes[-10]
    ) * 100




    if volume_ratio >= 3 and price_change > 2:

        signal = "STRONG_BUY"

        message = (
            "🐋 نشاط حيتان شرائي\n\n"
            "حجم التداول أعلى من المتوسط "
            "بشكل كبير\n"
            "مع ارتفاع السعر"
        )



    elif volume_ratio >= 3 and price_change < -2:

        signal = "STRONG_SELL"

        message = (
            "🐋 خروج حيتان\n\n"
            "ضغط بيع كبير تم اكتشافه"
        )



    elif volume_ratio >= 1.8:

        signal = "WATCH"

        message = (
            "👀 نشاط غير طبيعي في الحجم\n"
            "مراقبة الحركة القادمة"
        )



    else:

        signal = "WAIT"

        message = (
            "لا يوجد نشاط حيتان واضح"
        )



    return {

        "school": "Whales",

        "signal": signal,

        "volume_ratio": round(
            volume_ratio,
            2
        ),

        "price_change": round(
            price_change,
            2
        ),

        "message": message

    }
