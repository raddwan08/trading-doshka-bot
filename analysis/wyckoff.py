def wyckoff_analysis(df, symbol):

    close = df["close"]
    volume = df["volume"]


    last = close.iloc[-1]
    avg_volume = volume.mean()


    if volume.iloc[-1] > avg_volume * 1.8:

        phase = "Accumulation / Smart Money Activity"

        signal = "احتمال دخول سيولة كبيرة"

    else:

        phase = "Normal Trading"

        signal = "انتظار تأكيد"


    return {

        "text":f"""
📊 Wyckoff Analysis

عملة:
{symbol}USDT

المرحلة:
{phase}

الإشارة:
{signal}

السعر الحالي:
{last:.4f}

التحليل يعتمد على:
- Volume
- Price Action
- Accumulation
- Distribution

""",

        "entry":[last],

        "levels":[last]

    }
