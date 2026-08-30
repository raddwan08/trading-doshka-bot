import io
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def make_chart(data, result, title="Trading Analysis"):

    fig, ax = plt.subplots(figsize=(12, 6))

    times = [x["time"] for x in data]

    for i, candle in enumerate(data):

        open_price = candle["open"]
        close_price = candle["close"]
        high = candle["high"]
        low = candle["low"]

        ax.plot(
            [times[i], times[i]],
            [low, high],
            linewidth=1
        )

        ax.plot(
            [times[i], times[i]],
            [open_price, close_price],
            linewidth=4
        )


    # رسم مستويات التحليل إن وجدت
    levels = []

    if "support" in result:
        levels.extend(result["support"])

    if "resistance" in result:
        levels.extend(result["resistance"])

    if "entry" in result:
        levels.append(result["entry"])

    if "stop" in result:
        levels.append(result["stop"])

    if "target" in result:
        levels.append(result["target"])


    for level in levels:
        ax.axhline(level, alpha=0.4)


    ax.set_title(title)

    ax.grid(True)

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%m-%d %H:%M")
    )

    plt.xticks(rotation=45)

    plt.tight_layout()


    image = io.BytesIO()

    plt.savefig(
        image,
        format="png",
        dpi=120
    )

    plt.close()

    image.seek(0)

    return image
