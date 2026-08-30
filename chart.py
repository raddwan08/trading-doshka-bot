# chart.py

import io
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle



def create_chart(data, analysis, symbol, school):

    fig, ax = plt.subplots(
        figsize=(13,7)
    )


    # بيانات الشموع

    for i,candle in enumerate(data):

        open_price = candle["open"]
        close_price = candle["close"]
        high = candle["high"]
        low = candle["low"]


        color = (
            "green"
            if close_price >= open_price
            else "red"
        )


        # الذيل

        ax.plot(
            [i,i],
            [low,high]
        )


        # جسم الشمعة

        rect = Rectangle(
            (
                i-min(0.3,0.3),
                min(open_price,close_price)
            ),
            0.6,
            abs(close_price-open_price)
            if close_price != open_price
            else 0.001,

        )


        rect.set_facecolor(color)

        ax.add_patch(rect)



    closes=[
        x["close"]
        for x in data
    ]


    # المتوسطات

    if len(closes)>20:

        ma20=sum(closes[-20:])/20

        ax.axhline(
            ma20,
            alpha=.5,
            linestyle="--",
            label="MA20"
        )



    price=closes[-1]


    # تحديد الصفقة حسب التحليل

    signal=analysis["signal"]


    if "شراء" in signal:


        entry=price

        stop=price*0.97

        target=price*1.06


        ax.scatter(
            len(data)-1,
            entry,
            marker="^",
            s=120
        )


        ax.text(
            len(data)-5,
            entry,
            "ENTRY BUY"
        )


        ax.axhline(
            stop,
            linestyle=":"
        )


        ax.axhline(
            target,
            linestyle=":"
        )


    elif "بيع" in signal:


        entry=price

        stop=price*1.03

        target=price*0.94


        ax.scatter(
            len(data)-1,
            entry,
            marker="v",
            s=120
        )


        ax.text(
            len(data)-5,
            entry,
            "ENTRY SELL"
        )


        ax.axhline(
            stop,
            linestyle=":"
        )


        ax.axhline(
            target,
            linestyle=":"
        )



    ax.set_title(
        f"{symbol} / USDT\n"
        f"School: {school}\n"
        f"{signal} - Confidence {analysis['confidence']}%"
    )


    ax.grid(alpha=.3)


    ax.set_xlim(
        0,
        len(data)
    )


    ax.set_xticks([])


    plt.tight_layout()


    buffer=io.BytesIO()

    plt.savefig(
        buffer,
        format="png",
        dpi=150
    )


    plt.close(fig)


    buffer.seek(0)

    return buffer
