SCHOOL_NAME = "🔒 تحليل TVL"

REQUIRES_CANDLES = False


def analyze(data):

    if not data:

        return {
            "school": "TVL",
            "signal": "WAIT",
            "message": "لا توجد بيانات TVL.",
            "chart": None
        }


    tvl_value = float(
        data.get("tvl", 0)
    )


    change = float(
        data.get(
            "tvl_change_30d",
            0
        )
    )


    # =================================
    # SIGNAL
    # =================================

    if change > 10:

        signal = "BUY"

        message = (
            "📈 نمو قوي في السيولة المقفلة TVL.\n"
            "💰 تدفق السيولة إيجابي."
        )


    elif change < -10:

        signal = "SELL"

        message = (
            "📉 انخفاض واضح في TVL.\n"
            "⚠️ خروج سيولة من النظام."
        )


    else:

        signal = "WAIT"

        message = (
            "📊 TVL مستقر نسبياً.\n"
            "لا توجد تغيرات قوية في السيولة."
        )


    # =================================
    # CHART DATA
    # =================================

    chart_data = {

        "type": "bar",

        "title": "TVL Analysis",

        "labels": [
            "TVL",
            "30d Change"
        ],

        "values": [
            tvl_value,
            change
        ]

    }


    return {

        "school": "TVL",

        "signal": signal,

        "message": message,

        "tvl": tvl_value,

        "tvl_change_30d": change,

        "chart": chart_data

    }        data.get(
            "tvl_change_30d",
            0
        )

    )


    # =================================
    # SIGNAL
    # =================================

    if change > 10:


        signal = "BUY"


        message = (

            "📈 نمو قوي في السيولة "
            "المقفلة TVL.\n"
            "💰 تدفق السيولة إيجابي."

        )


    elif change < -10:


        signal = "SELL"


        message = (

            "📉 انخفاض واضح في TVL.\n"
            "⚠️ خروج سيولة من النظام."

        )


    else:


        signal = "WAIT"


        message = (

            "📊 TVL مستقر نسبياً.\n"
            "لا توجد تغيرات قوية "
            "في السيولة."

        )


    return {

        "school": "TVL",

        "signal": signal,

        "message": message,

        "tvl": tvl_value,

        "tvl_change_30d": change,


        "chart": {

            "values": {

                "TVL":
                    tvl_value,

                "30d Change":
                    change

            }

        }

    }
