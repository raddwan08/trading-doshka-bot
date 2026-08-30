import random
from datetime import datetime


def direction(score):

    if score >= 65:
        return "🟢 شراء محتمل"

    elif score <= 35:
        return "🔴 بيع محتمل"

    else:
        return "🟡 انتظار"



# 1) التحليل الكلاسيكي
def classic(data):

    prices = data

    change = (
        prices[-1] - prices[0]
    ) / prices[0] * 100


    score = 50 + change


    return f"""
📈 <b>التحليل الكلاسيكي</b>

تغير السعر:
{change:.2f}%

RSI تقديري:
{random.randint(35,70)}

EMA:
اتجاه {'صاعد' if change>0 else 'هابط'}

النتيجة:
{direction(score)}
"""



# 2) وايكوف
def wyckoff(data):

    volume=random.randint(
        50,
        200
    )


    if volume > 130:

        phase="تجميع قوي من السوق"

    else:

        phase="حركة طبيعية"


    return f"""
📊 <b>تحليل وايكوف</b>

مرحلة السوق:
{phase}

قوة الحجم:
{volume}%

المراقبة:
مناطق التجميع والتوزيع

الإشارة:
{"🟢 دخول محتمل" if volume>130 else "🟡 انتظار"}
"""



# 3) إليوت
def elliott(data):

    wave=random.randint(
        1,
        5
    )


    return f"""
🌊 <b>تحليل موجات إليوت</b>

الموجة الحالية:
الموجة {wave}

البنية:
{'صعودية' if wave in [1,3,5] else 'تصحيحية'}

النصيحة:
متابعة القمة والقاع الأخير
"""



# 4) هارمونيك
def harmonic(data):

    pattern=random.choice(
        [
            "Gartley",
            "Bat",
            "Butterfly"
        ]
    )


    ratio=random.choice(
        [
            "0.618",
            "0.786",
            "0.886"
        ]
    )


    return f"""
🦋 <b>تحليل هارمونيك</b>

النموذج:
{pattern}

نسبة فيبوناتشي:
{ratio}

الحالة:
منطقة مراقبة انعكاس محتملة
"""



# 5) الحيتان
def whales(data):

    volume=random.randint(
        100,
        300
    )


    return f"""
🐋 <b>تحليل الحيتان</b>

نشاط الحجم:
{volume}%

حالة السوق:
{"وجود حركة كبيرة" if volume>180 else "نشاط عادي"}

المراقبة:
الشموع ذات الحجم المرتفع
"""



# 6) السيولة
def liquidity(data):

    buy=random.randint(
        40,
        80
    )

    sell=100-buy


    return f"""
🔒 <b>تحليل السيولة</b>

ضغط الشراء:
{buy}%

ضغط البيع:
{sell}%

الاتجاه:
{"شراء" if buy>sell else "بيع"}
"""



async def run_analysis(symbol, school):

    # بيانات تجريبية مؤقتة
    # سيتم ربط Binance لاحقاً

    data=[
        random.uniform(90,110)
        for _ in range(100)
    ]


    header=f"""
💰 العملة: {symbol}
🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

"""


    if school=="classic":
        result=classic(data)

    elif school=="wyckoff":
        result=wyckoff(data)

    elif school=="elliott":
        result=elliott(data)

    elif school=="harmonic":
        result=harmonic(data)

    elif school=="whales":
        result=whales(data)

    elif school=="liquidity":
        result=liquidity(data)

    else:
        result="❌ مدرسة غير موجودة"


    return header + result
