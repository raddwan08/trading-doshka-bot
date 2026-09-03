import numpy as np


SCHOOL_NAME = "🦋 تحليل هارمونيك"

REQUIRES_CANDLES = True


# =====================================
# FIND PIVOTS
# =====================================

def find_pivots(
    highs,
    lows,
    window=3
):

    pivots = []


    for i in range(

        window,

        len(highs) - window

    ):


        high_section = (

            highs[
                i - window:
                i + window + 1
            ]

        )


        low_section = (

            lows[
                i - window:
                i + window + 1
            ]

        )


        # Pivot High

        if highs[i] == max(
            high_section
        ):

            pivots.append(

                {

                    "index":
                        i,

                    "price":
                        float(
                            highs[i]
                        ),

                    "type":
                        "HIGH"

                }

            )


        # Pivot Low

        elif lows[i] == min(
            low_section
        ):

            pivots.append(

                {

                    "index":
                        i,

                    "price":
                        float(
                            lows[i]
                        ),

                    "type":
                        "LOW"

                }

            )


    return pivots


# =====================================
# CHECK HARMONIC RATIOS
# =====================================

def calculate_ratio(
    a,
    b
):

    if a == 0:

        return 0


    return abs(b / a)


# =====================================
# MAIN ANALYSIS
# =====================================

def analyze(
    candles
):

    if not candles or len(candles) < 60:

        return {

            "school": "Harmonic",

            "signal": "WAIT",

            "message": (
                "بيانات غير كافية "
                "للبحث عن نموذج هارمونيك."
            )

        }


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


    closes = np.array(

        [

            float(
                candle["close"]
            )

            for candle in candles

        ]

    )


    pivots = find_pivots(

        highs,

        lows

    )


    # =================================
    # NEED 5 POINTS
    # =================================

    if len(pivots) < 5:


        return {

            "school": "Harmonic",

            "signal": "WAIT",

            "pattern": "No Pattern",

            "message": (
                "لم يتم العثور على "
                "نموذج هارمونيك واضح."
            ),

            "chart": {

                "points":
                    []

            }

        }


    # =================================
    # LAST 5 PIVOTS
    # =================================

    points = pivots[-5:]


    x_point = points[0]

    a_point = points[1]

    b_point = points[2]

    c_point = points[3]

    d_point = points[4]


    xa = abs(

        a_point["price"] -
        x_point["price"]

    )


    ab = abs(

        b_point["price"] -
        a_point["price"]

    )


    bc = abs(

        c_point["price"] -
        b_point["price"]

    )


    cd = abs(

        d_point["price"] -
        c_point["price"]

    )


    ab_ratio = calculate_ratio(
        xa,
        ab
    )


    bc_ratio = calculate_ratio(
        ab,
        bc
    )


    cd_ratio = calculate_ratio(
        bc,
        cd
    )


    pattern = (
        "Potential Harmonic"
    )


    signal = "WAIT"


    message = (

        "🦋 تم العثور على نقاط Pivot "
        "يمكن استخدامها لتحليل "
        "نموذج هارمونيك."

    )


    # =================================
    # GARTLEY-LIKE
    # =================================

    if (

        0.55 <= ab_ratio <= 0.70

        and

        0.38 <= bc_ratio <= 0.95

        and

        1.20 <= cd_ratio <= 1.80

    ):


        pattern = "Gartley"


        # إذا كانت D منخفضة
        if d_point["price"] < c_point["price"]:


            signal = "BUY"


            message = (

                "🦋 تم اكتشاف نموذج "
                "Gartley محتمل.\n"
                "📈 منطقة D قد تمثل "
                "منطقة انعكاس صعودي."

            )


        else:


            signal = "SELL"


            message = (

                "🦋 تم اكتشاف نموذج "
                "Gartley محتمل.\n"
                "📉 منطقة D قد تمثل "
                "منطقة انعكاس هبوطي."

            )


    # =================================
    # BUTTERFLY-LIKE
    # =================================

    elif (

        0.70 <= ab_ratio <= 0.85

        and

        0.38 <= bc_ratio <= 0.95

        and

        1.50 <= cd_ratio <= 2.80

    ):


        pattern = "Butterfly"


        if d_point["price"] < c_point["price"]:


            signal = "BUY"


            message = (

                "🦋 نموذج Butterfly "
                "محتمل.\n"
                "📈 احتمال انعكاس صعودي "
                "من منطقة D."

            )


        else:


            signal = "SELL"


            message = (

                "🦋 نموذج Butterfly "
                "محتمل.\n"
                "📉 احتمال انعكاس هبوطي "
                "من منطقة D."

            )


    # =================================
    # CONNECTION
    # =================================

    x_values = [

        x_point["index"],

        a_point["index"],

        b_point["index"],

        c_point["index"],

        d_point["index"]

    ]


    y_values = [

        x_point["price"],

        a_point["price"],

        b_point["price"],

        c_point["price"],

        d_point["price"]

    ]


    # =================================
    # CHART POINTS
    # =================================

    chart_points = [

        {

            "index":
                x_point["index"],

            "price":
                x_point["price"],

            "label":
                "X"

        },

        {

            "index":
                a_point["index"],

            "price":
                a_point["price"],

            "label":
                "A"

        },

        {

            "index":
                b_point["index"],

            "price":
                b_point["price"],

            "label":
                "B"

        },

        {

            "index":
                c_point["index"],

            "price":
                c_point["price"],

            "label":
                "C"

        },

        {

            "index":
                d_point["index"],

            "price":
                d_point["price"],

            "label":
                "D"

        }

    ]


    return {

        "school": "Harmonic",

        "signal": signal,

        "pattern": pattern,

        "message": message,

        "ratios": {

            "AB":
                round(
                    ab_ratio,
                    3
                ),

            "BC":
                round(
                    bc_ratio,
                    3
                ),

            "CD":
                round(
                    cd_ratio,
                    3
                )

        },


        "chart": {

            "connections": [

                {

                    "x":
                        x_values,

                    "y":
                        y_values,

                    "label":
                        pattern

                }

            ],


            "points":
                chart_points

        }

    }
