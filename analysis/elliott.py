def elliott_analysis(df, symbol):

    close=df["close"]

    last=close.iloc[-1]


    change = (
        close.iloc[-1]
        -
        close.iloc[-20]
    )


    if change > 0:

        wave="Wave 3 / Bullish Structure"

        signal="الاتجاه صاعد"

    else:

        wave="Wave C Correction"

        signal="ضغط بيعي"



    return {

"text":f"""
🌊 Elliott Wave

{symbol}USDT

الموجة الحالية:
{wave}

الحالة:
{signal}

السعر:
{last:.4f}

تم تحليل:
- Higher High
- Higher Low
- Momentum

""",

"entry":[last],

"levels":[last]

}
