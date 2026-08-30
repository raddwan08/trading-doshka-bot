
from __future__ import annotations

import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


def make_chart(k, sig, title):
    if not k:
        raise ValueError("No candles")
    fig, ax = plt.subplots(figsize=(12, 7))
    dates = [x["time"] for x in k]

    for i, x in enumerate(k):
        # Wick
        ax.plot([dates[i], dates[i]], [x["low"], x["high"]], linewidth=1)
        # Body
        ax.plot(
            [dates[i], dates[i]],
            [x["open"], x["close"]],
            linewidth=4,
        )

    levels = (
        sig.get("sr", {}).get("supports", [])
        + sig.get("sr", {}).get("resistances", [])
        + sig.get("entry", [])
        + [sig.get("stop_loss")]
        + [sig.get("take_profit")]
    )
    for level in levels:
        if isinstance(level, (int, float)):
            ax.axhline(float(level), alpha=0.35, linewidth=1)

    ax.set_title(title)
    ax.set_ylabel("USDT")
    ax.grid(alpha=0.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    fig.autofmt_xdate()
    fig.tight_layout()

    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    output.seek(0)
    return output
