import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def make_chart(k, sig, title):
    fig, ax = plt.subplots(figsize=(12,7))
    dates=[x["time"] for x in k]
    for i,x in enumerate(k):
        up=x["close"]>=x["open"]
        # No fixed palette dependency; matplotlib chooses defaults.
        ax.plot([dates[i],dates[i]],[x["low"],x["high"]],lw=1)
        ax.plot([dates[i],dates[i]],[x["open"],x["close"]],lw=4)
    for level in (
        sig["sr"]["supports"]+sig["sr"]["resistances"]+
        sig["entry"]+[sig["stop_loss"]]+sig["take_profit"]
    ):
        ax.axhline(level,alpha=.35)
    ax.set_title(title)
    ax.grid(alpha=.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    plt.setp(ax.get_xticklabels(),rotation=45,ha="right")
    plt.tight_layout()
    b=io.BytesIO()
    fig.savefig(b,format="png",dpi=130)
    plt.close(fig)
    b.seek(0)
    return b
