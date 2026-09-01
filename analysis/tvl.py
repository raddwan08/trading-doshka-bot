id="tvl001"
def analyze(tvl_data):

    if not tvl_data:

        return {
            "signal": "WAIT",
            "message": "لا توجد بيانات TVL"
        }



    tvl = float(
        tvl_data.get(
            "tvl",
            0
        )
    )


    change = float(
        tvl_data.get(
            "tvl_change_30d",
            0
        )
    )



    score = 0



    # حجم السيولة

    if tvl > 1_000_000_000:

        score += 3

    elif tvl > 100_000_000:

        score += 2

    elif tvl > 10_000_000:

        score += 1



    # نمو السيولة

    if change > 20:

        score += 3

    elif change > 5:

        score += 2

    elif change < -10:

        score -= 2




    if score >= 5:

        signal = "STRONG_BUY"

        message = (
            "🔒 قوة TVL عالية\n\n"
            "السيولة تنمو بشكل قوي\n"
            "المشروع يظهر جذباً للسيولة"
        )



    elif score >= 3:

        signal = "BUY"

        message = (
            "🔒 TVL إيجابي\n"
            "هناك نمو في السيولة"
        )



    elif score <= 0:

        signal = "SELL"

        message = (
            "⚠️ ضعف في TVL\n"
            "خروج أو انخفاض السيولة"
        )



    else:

        signal = "WAIT"

        message = (
            "🔒 TVL مستقر\n"
            "لا توجد إشارة قوية"
        )



    return {

        "school": "TVL",

        "signal": signal,

        "tvl": tvl,

        "change_30d": change,

        "message": message

    }
