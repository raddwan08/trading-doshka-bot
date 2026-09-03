import numpy as np


SCHOOL_NAME = "🐋 تحليل الحيتان"

REQUIRES_CANDLES = True


# =====================================
# MAIN ANALYSIS
# =====================================

def analyze(
    candles
):

    if not candles or len(candles) < 30:

        return {

            "school": "Whales",

            "signal": "WAIT",

            "message": (
                "بيانات غير كافية "
                "لتحليل نشاط الحيتان."
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


    opens = np.array(

        [

            float(
                candle["open"]
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


    volumes = np.array(

        [

            float(
                candle.get(
                    "volume",
                    0
                )
            )

            for candle in candles

        ]

    )


    # =================================
    # AVERAGE VOLUME
    # =================================

    average_volume = np.mean(

        volumes[-20:-1]

    )


    current_volume = (
        volumes[-1]
    )


    if average_volume <= 0:

        volume_ratio = 0

    else:

        volume_ratio = (

            current_volume /
            average_volume

        )


    # =================================
    # FIND WHALE CANDLES
    # =================================

    whale_points = []


    whale_indices = []


    for index in range(
        len(volumes)
    ):


        recent_start = max(

            0,

            index - 20

        )


        recent_volumes = (

            volumes[
                recent_start:index
            ]

        )


        if len(
            recent_volumes
        ) < 5:

            continue


        avg = np.mean(
            recent_volumes
        )


        if avg <= 0:

            continue


        ratio = (

            volumes[index] /
            avg

        )


        if ratio >= 2:


            price = closes[index]


            whale_indices.append(
                index
            )


            whale_points.append(

                {

                    "index":
                        index,

                    "price":
                        float(price),

                    "label":
                        f"🐋 {round(ratio, 1)}x"

                }

            )


    # =================================
    # DIRECTION
    # =================================

    current_close = (
        closes[-1]
    )


    current_open = (
        opens[-1]
    )


    recent_low = min(
        lows[-20:]
    )


    recent_high = max(
        highs[-20:]
    )


    support = recent_low

    resistance = recent_high


    if (

        volume_ratio >= 1.5

        and

        current_close >
        current_open

    ):


        signal = "BUY"


        message = (

            "🐋 تم رصد نشاط شرائي "
            "مرتفع مقارنة بمتوسط الحجم.\n"
            "📈 الحجم والسعر يدعمان "
            "الضغط الشرائي."

        )


    elif (

        volume_ratio >= 1.5

        and

        current_close <
        current_open

    ):


        signal = "SELL"


        message = (

            "🐋 تم رصد نشاط بيعي "
            "مرتفع مقارنة بمتوسط الحجم.\n"
            "📉 هناك ضغط بيع واضح."

        )


    else:


        signal = "WAIT"


        message = (

            "🐋 لا يوجد حالياً نشاط "
            "استثنائي قوي للحيتان."

        )


    # =================================
    # RESULT
    # =================================

    return {

        "school": "Whales",

        "signal": signal,

        "message": message,

        "volume_ratio": round(

            float(volume_ratio),

            2

        ),

        "support": round(

            float(support),

            8

        ),

        "resistance": round(

            float(resistance),

            8

        ),


        "chart": {

            "points":
                whale_points,


            "levels": [

                {

                    "price":
                        support,

                    "label":
                        "Whale Support",

                    "style":
                        "--"

                },

                {

                    "price":
                        resistance,

                    "label":
                        "Whale Resistance",

                    "style":
                        "--"

                }

            ]

        }

    }
