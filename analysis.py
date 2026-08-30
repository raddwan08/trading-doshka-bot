
# analysis.py

import statistics


def last_price(data):
    return data[-1]["close"]



def average_volume(data, period=20):

    vols = [
        x["volume"]
        for x in data[-period:]
    ]

    return statistics.mean(vols)



# =========================
# وايكوف
# =========================

def wyckoff(data):

    price = last_price(data)

    avg = statistics.mean(
        [x["close"] for x in data[-50:]]
    )

    volume = average_volume(data)

    last_volume = data[-1]["volume"]


    if price > avg and last_volume > volume:

        return {
            "signal":"شراء",
            "reason":
            "مرحلة تراكم وايكوف مع زيادة حجم",
            "confidence":78
        }


    elif price < avg and last_volume > volume:

        return {
            "signal":"بيع",
            "reason":
            "توزيع وايكوف وضغط بيعي",
            "confidence":75
        }


    return {
        "signal":"انتظار",
        "reason":
        "مرحلة توازن سعري",
        "confidence":55
    }




# =========================
# إليوت
# =========================

def elliott(data):

    closes=[
        x["close"]
        for x in data[-30:]
    ]


    rising=sum(
        closes[i]>closes[i-1]
        for i in range(1,len(closes))
    )


    if rising >=20:

        return {
            "signal":"شراء",
            "reason":
            "احتمال اكتمال موجة دافعة صاعدة",
            "confidence":72
        }


    if rising <=8:

        return {
            "signal":"بيع",
            "reason":
            "احتمال نهاية موجة هابطة",
            "confidence":70
        }


    return {
        "signal":"انتظار",
        "reason":
        "الموجة غير واضحة",
        "confidence":50
    }




# =========================
# هارمونيك
# =========================

def harmonic(data):

    high=max(
        x["high"]
        for x in data[-50:]
    )

    low=min(
        x["low"]
        for x in data[-50:]
    )


    current=last_price(data)


    fib=(current-low)/(high-low)


    if 0.60 < fib < 0.65:

        return {
            "signal":"شراء",
            "reason":
            "منطقة تصحيح هارمونيك محتملة",
            "confidence":76
        }


    if 0.35 < fib < 0.40:

        return {
            "signal":"بيع",
            "reason":
            "منطقة انعكاس هارمونيك محتملة",
            "confidence":74
        }


    return {
        "signal":"انتظار",
        "reason":
        "لا يوجد نموذج هارمونيك مكتمل",
        "confidence":45
    }




# =========================
# التحليل الكلاسيكي
# =========================

def classic(data):

    closes=[
        x["close"]
        for x in data
    ]


    ema20=statistics.mean(
        closes[-20:]
    )

    ema50=statistics.mean(
        closes[-50:]
    )

    price=closes[-1]


    if price > ema20 > ema50:

        return {
            "signal":"شراء",
            "reason":
            "اتجاه صاعد EMA",
            "confidence":80
        }


    if price < ema20 < ema50:

        return {
            "signal":"بيع",
            "reason":
            "اتجاه هابط EMA",
            "confidence":80
        }


    return {
        "signal":"انتظار",
        "reason":
        "تضارب المتوسطات",
        "confidence":50
    }




# =========================
# الحيتان
# =========================

def whales(data):

    avg=average_volume(data)

    current=data[-1]


    if current["volume"] > avg*3:


        if current["close"] > current["open"]:

            return {
                "signal":"شراء قوي",
                "reason":
                "دخول حجم حوت شرائي",
                "confidence":85
            }


        else:

            return {
                "signal":"بيع قوي",
                "reason":
                "تصريف حوت",
                "confidence":85
            }


    return {
        "signal":"انتظار",
        "reason":
        "لا يوجد نشاط حيتان",
        "confidence":40
    }




# ربط المدارس

SCHOOLS_ANALYSIS = {

    "wyckoff":wyckoff,
    "elliott":elliott,
    "harmonic":harmonic,
    "classic":classic,
    "whales":whales

}



def run_analysis(name,data):

    if name not in SCHOOLS_ANALYSIS:
        return {
            "signal":"خطأ",
            "reason":"مدرسة غير موجودة",
            "confidence":0
        }


    return SCHOOLS_ANALYSIS[name](data)
