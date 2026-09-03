import numpy as np


SCHOOL_NAME = "📈 تحليل وايكوف"

REQUIRES_CANDLES = True


# =====================================
# MAIN ANALYSIS
# =====================================

def analyze(
    candles
):

    if not candles or len(candles) < 50:

        return {

            "school": "Wyckoff",

            "signal": "WAIT",

            "message": (
                "بيانات غير كافية "
                "لتحليل Wyckoff."
            )

        }


    opens = np.array(

        [

            float(
                candle["open"]
            )

            for candle in candles

        ]

    )


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
    # RECENT RANGE
    # =================================

    range_high = max(
        highs[-30:]
    )


    range_low = min(
        lows[-30:]
    )


    current_price = (
        closes[-1]
    )


    range_size = (

        range_high -
        range_low

    )


    if range_size <= 0:

        range_position = 0.5

    else:

        range_position = (

            current_price -
            range_low

        ) / range_size


    # =================================
    # VOLUME
    # =================================

    recent_volume = np.mean(

        volumes[-10:]

    )


    previous_volume = np.mean(

        volumes[-30:-10]

    )


    if previous_volume <= 0:

        volume_ratio = 1

    else:

        volume_ratio = (

            recent_volume /
            previous_volume

        )


    # =================================
    # PRICE TREND
    # =================================

    old_price = np.mean(
        closes[-30:-20]
    )


    recent_price = np.mean(
        closes[-10:]
    )


    if recent_price > old_price:

        trend = "UP"

    else:

        trend = "DOWN"


    # =================================
    # ACCUMULATION
    # =================================

    if (

        trend == "UP"

        and

        range_position < 0.55

        and

        volume_ratio > 0.9

    ):


        phase = "Accumulation"


        signal = "BUY"


        message = (

            "📦 احتمال وجود مرحلة "
            "تجميع Accumulation.\n"
            "🐂 السعر بدأ يظهر قوة "
            "بعد نطاق تداول."

        )


        zone_low = range_low

        zone_high = (

            range_low +
            range_size * 0.45

        )


    # =================================
    # DISTRIBUTION
    # =================================

    elif (

        trend == "DOWN"

        and

        range_position > 0.45

        and

        volume_ratio > 0.9

    ):


        phase = "Distribution"


        signal = "SELL"


        message = (

            "📦 احتمال وجود مرحلة "
            "تصريف Distribution.\n"
            "🐻 السعر يظهر ضعفاً "
            "بعد التداول قرب القمم."

        )


        zone_low = (

            range_high -
            range_size * 0.45

        )


        zone_high = range_high


    else:


        phase = "Neutral"


        signal = "WAIT"


        message = (

            "📊 السوق في نطاق محايد.\n"
            "لا توجد حالياً مرحلة Wyckoff "
            "واضحة."

        )


        zone_low = range_low

        zone_high = range_high


    # =================================
    # BREAKOUT LEVELS
    # =================================

    support = range_low

    resistance = range_high


    # =================================
    # RESULT
    # =================================

    return {

        "school": "Wyckoff",

        "signal": signal,

        "message": message,

        "phase": phase,

        "support": round(

            float(support),

            8

        ),

        "resistance": round(

            float(resistance),

            8

        ),

        "volume_ratio": round(

            float(volume_ratio),

            2

        ),


        "chart": {

            "zones": [

                {

                    "low":
                        float(zone_low),

                    "high":
                        float(zone_high)

                }

            ],


            "levels": [

                {

                    "price":
                        float(support),

                    "label":
                        "Wyckoff Support",

                    "style":
                        "--"

                },

                {

                    "price":
                        float(resistance),

                    "label":
                        "Wyckoff Resistance",

                    "style":
                        "--"

                }

            ],


            "points": [

                {

                    "index":
                        len(candles) - 1,

                    "price":
                        float(current_price),

                    "label":
                        phase

                }

            ]

        }

    }
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
