def harmonic_analysis(df, symbol):

    high=df["high"]

    low=df["low"]

    last=df["close"].iloc[-1]


    range_value = (
        high.max()
        -
        low.min()
    )


    return {


"text":f"""
🦋 Harmonic Pattern

{symbol}USDT


Current Price:
{last:.4f}


Pattern Scan:

- Gartley
- Bat
- Butterfly
- Crab


Range:
{range_value:.4f}


الحالة:
يتم انتظار اكتمال النموذج

""",

"entry":[last],

"levels":[last]

}
