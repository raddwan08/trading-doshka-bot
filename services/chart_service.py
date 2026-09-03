import os
import pandas as pd
import mplfinance as mpf


class ChartService:

    def create_chart(
        self,
        symbol,
        candles
    ):

        df = pd.DataFrame(
            candles
        )

        df["time"] = pd.to_datetime(
            df["time"],
            unit="ms"
        )

        df.set_index(
            "time",
            inplace=True
        )

        df.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume"
            },
            inplace=True
        )

        os.makedirs(
            "charts",
            exist_ok=True
        )

        path = f"charts/{symbol}_analysis.png"

        mpf.plot(

            df,

            type="candle",

            volume=True,

            style="yahoo",

            title=f"{symbol} Analysis",

            savefig=path

        )

        return path
