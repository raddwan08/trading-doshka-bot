import os

import pandas as pd

import mplfinance as mpf


class ChartService:


    def create_chart(

        self,

        symbol,

        candles,

        school,

        result=None

    ):


        # =========================
        # تحويل البيانات
        # =========================

        df = pd.DataFrame(
            candles
        )


        # التأكد من وجود الوقت

        if "time" not in df.columns:

            df["time"] = pd.date_range(

                end=pd.Timestamp.now(),

                periods=len(df),

                freq="4H"

            )


        else:

            df["time"] = pd.to_datetime(

                df["time"],

                unit="ms"

            )


        df.set_index(

            "time",

            inplace=True

        )


        # =========================
        # الأعمدة المطلوبة
        # =========================

        df = df.rename(

            columns={

                "open": "Open",

                "high": "High",

                "low": "Low",

                "close": "Close",

                "volume": "Volume"

            }

        )


        # =========================
        # اسم الملف
        # =========================

        filename = (

            f"/tmp/"

            f"{symbol}_"

            f"{school}_"

            f"chart.png"

        )


        # =========================
        # خطوط التحليل
        # =========================

        hlines = []


        # الدعم

        if result:

            support = result.get(
                "support"
            )


            if support is not None:

                hlines.append(
                    support
                )


            # المقاومة

            resistance = result.get(
                "resistance"
            )


            if resistance is not None:

                hlines.append(
                    resistance
                )


        # =========================
        # عنوان المدرسة
        # =========================

        school_names = {

            "analysis_wyckoff":
                "Wyckoff",

            "analysis_harmonic":
                "Harmonic",

            "analysis_classic":
                "Classic",

            "analysis_whales":
                "Whales"

        }


        school_name = school_names.get(

            school,

            school

        )


        # =========================
        # إعداد الرسم
        # =========================

        plot_kwargs = {

            "type": "candle",

            "volume": True,

            "title":
                f"{symbol} Analysis - "
                f"{school_name}",

            "ylabel":
                "Price",

            "ylabel_lower":
                "Volume",

            "figsize":
                (14, 9),

            "savefig":
                filename

        }


        # إضافة الدعم والمقاومة

        if hlines:

            plot_kwargs["hlines"] = {

                "hlines":
                    hlines,

                "linewidths":
                    [1.5] * len(hlines),

                "alpha":
                    0.8

            }


        # =========================
        # رسم الشارت
        # =========================

        mpf.plot(

            df,

            **plot_kwargs

        )


        return filename
