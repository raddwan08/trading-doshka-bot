def whales_analysis(df, symbol):


    volume=df["volume"]

    last_volume=volume.iloc[-1]

    average=volume.mean()

    price=df["close"].iloc[-1]


    if last_volume > average*2:

        status="🐋 حركة حوت محتملة"

    else:

        status="لا توجد حركة غير طبيعية"



    return {


"text":f"""
🐋 Whales Detector


{symbol}USDT


الحالة:

{status}


Volume:

Current:
{last_volume:.2f}


Average:
{average:.2f}


Price:
{price:.4f}


تم فحص:
- Volume Spike
- Large Orders
- Abnormal Activity


""",

"entry":[price],

"levels":[price]

}
