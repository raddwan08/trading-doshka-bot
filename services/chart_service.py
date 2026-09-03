import os

import pandas as pd
import mplfinance as mpf


class ChartService:

    def create_chart(
        self,
        symbol,
        candles,
        school
    ):

        data = []


        for candle in candles:

            data.append({

                "time":
                    pd.to_datetime(
                        candle["time"],
                        unit="ms"
                    ),

                "Open":
                    float(
                        candle["open"]
                    ),

                "High":
                    float(
                        candle["high"]
                    ),

                "Low":
                    float(
                        candle["low"]
                    ),

                "Close":
                    float(
                        candle["close"]
                    ),

                "Volume":
                    float(
                        candle["volume"]
                    )

            })


        df = pd.DataFrame(
            data
        )


        df.set_index(
            "time",
            inplace=True
        )


        os.makedirs(
            "charts",
            exist_ok=True
        )


        filename = (
            f"charts/"
            f"{symbol}_{school}.png"
        )


        mpf.plot(

            df,

            type="candle",

            volume=True,

            style="yahoo",

            title=(
                f"{symbol} Analysis - "
                f"{school.replace('analysis_', '').title()}"
            ),

            ylabel="Price",

            figsize=(
                12,
                8
            ),

            savefig=dict(

                fname=filename,

                dpi=150,

                bbox_inches="tight"

            )

        )


        return filename
