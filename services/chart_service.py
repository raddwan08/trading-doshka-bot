import os
import uuid
import logging

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


logger = logging.getLogger(__name__)


class ChartService:

    def __init__(self):
        self.chart_dir = "charts"

        os.makedirs(
            self.chart_dir,
            exist_ok=True
        )

    # =====================================
    # CREATE CHART
    # =====================================

    def create_chart(
        self,
        symbol,
        candles,
        school,
        analysis_result=None
    ):

        analysis_result = analysis_result or {}

        # =================================
        # NON-CANDLE DATA
        # Example: TVL
        # =================================

        if not candles:

            return self.create_data_chart(
                symbol=symbol,
                school=school,
                result=analysis_result
            )

        # =================================
        # EXTRACT CANDLE DATA
        # =================================

        opens = [
            float(candle["open"])
            for candle in candles
        ]

        highs = [
            float(candle["high"])
            for candle in candles
        ]

        lows = [
            float(candle["low"])
            for candle in candles
        ]

        closes = [
            float(candle["close"])
            for candle in candles
        ]

        volumes = [
            float(candle.get("volume", 0))
            for candle in candles
        ]

        x = list(range(len(candles)))

        # =================================
        # CREATE FIGURE
        # =================================

        fig, (
            ax_price,
            ax_volume
        ) = plt.subplots(
            2,
            1,
            figsize=(14, 9),
            sharex=True,
            gridspec_kw={
                "height_ratios": [
                    4,
                    1
                ]
            }
        )

        # =================================
        # TITLE
        # =================================

        school_title = analysis_result.get(
            "school",
            school.title()
        )

        fig.suptitle(
            f"{symbol} Analysis - {school_title}",
            fontsize=20,
            fontweight="bold"
        )

        # =================================
        # DRAW CANDLES
        # =================================

        for i in x:

            open_price = opens[i]
            close_price = closes[i]
            high_price = highs[i]
            low_price = lows[i]

            if close_price >= open_price:
                color = "green"
            else:
                color = "red"

            # Wick

            ax_price.plot(
                [i, i],
                [
                    low_price,
                    high_price
                ],
                color="black",
                linewidth=1
            )

            # Candle body

            body_bottom = min(
                open_price,
                close_price
            )

            body_height = abs(
                close_price - open_price
            )

            if body_height == 0:

                body_height = (
                    high_price - low_price
                ) * 0.02

            # حماية إضافية

            if body_height == 0:
                body_height = 0.00000001

            rectangle = Rectangle(
                (
                    i - 0.3,
                    body_bottom
                ),
                0.6,
                body_height,
                facecolor=color,
                edgecolor=color,
                alpha=0.8
            )

            ax_price.add_patch(
                rectangle
            )

        # =================================
        # VOLUME
        # =================================

        volume_colors = []

        for i in x:

            if closes[i] >= opens[i]:
                volume_colors.append("green")
            else:
                volume_colors.append("red")

        ax_volume.bar(
            x,
            volumes,
            color=volume_colors,
            alpha=0.5
        )

        # =================================
        # ANALYSIS OVERLAYS
        # =================================

        self.apply_analysis_overlays(
            ax=ax_price,
            x=x,
            candles=candles,
            result=analysis_result
        )

        # =================================
        # COMMON LEVELS
        # =================================

        self.apply_common_levels(
            ax=ax_price,
            result=analysis_result
        )

        # =================================
        # CURRENT SIGNAL
        # =================================

        signal = analysis_result.get(
            "signal",
            "WAIT"
        )

        current_price = closes[-1]

        ax_price.text(
            0.02,
            0.95,
            f"Signal: {signal}",
            transform=ax_price.transAxes,
            fontsize=14,
            verticalalignment="top",
            bbox={
                "boxstyle": "round",
                "alpha": 0.7
            }
        )

        ax_price.axhline(
            current_price,
            linestyle=":",
            alpha=0.5,
            label=f"Current {current_price}"
        )

        # =================================
        # STYLE
        # =================================

        ax_price.set_ylabel(
            "Price"
        )

        ax_volume.set_ylabel(
            "Volume"
        )

        ax_price.grid(
            alpha=0.3
        )

        ax_volume.grid(
            alpha=0.3
        )

        # لا تظهر legend إذا لم توجد عناصر

        handles, labels = (
            ax_price.get_legend_handles_labels()
        )

        if handles:
            ax_price.legend(
                loc="upper left"
            )

        plt.tight_layout()

        # =================================
        # SAVE FILE
        # =================================

        filename = (
            f"{symbol}_"
            f"{school}_"
            f"{uuid.uuid4().hex}.png"
        )

        path = os.path.join(
            self.chart_dir,
            filename
        )

        plt.savefig(
            path,
            dpi=150,
            bbox_inches="tight"
        )

        plt.close(fig)

        return path

    # =====================================
    # COMMON LEVELS
    # =====================================

    def apply_common_levels(
        self,
        ax,
        result
    ):

        support = result.get(
            "support"
        )

        resistance = result.get(
            "resistance"
        )

        target = result.get(
            "target"
        )

        stop_loss = result.get(
            "stop_loss"
        )

        # SUPPORT

        if support is not None:

            ax.axhline(
                float(support),
                linestyle="--",
                linewidth=1.5,
                label=f"Support {support}"
            )

        # RESISTANCE

        if resistance is not None:

            ax.axhline(
                float(resistance),
                linestyle="--",
                linewidth=1.5,
                label=f"Resistance {resistance}"
            )

        # TARGET

        if target is not None:

            ax.axhline(
                float(target),
                linestyle=":",
                linewidth=2,
                label=f"Target {target}"
            )

        # STOP LOSS

        if stop_loss is not None:

            ax.axhline(
                float(stop_loss),
                linestyle=":",
                linewidth=2,
                label=f"Stop Loss {stop_loss}"
            )

    # =====================================
    # GENERIC ANALYSIS OVERLAYS
    # =====================================

    def apply_analysis_overlays(
        self,
        ax,
        x,
        candles,
        result
    ):

        chart_data = result.get(
            "chart",
            {}
        )

        # =================================
        # HORIZONTAL LEVELS
        # =================================

        levels = chart_data.get(
            "levels",
            []
        )

        for level in levels:

            try:

                price = level.get(
                    "price"
                )

                if price is None:
                    continue

                ax.axhline(
                    float(price),
                    linestyle=level.get(
                        "style",
                        "--"
                    ),
                    linewidth=level.get(
                        "width",
                        1.5
                    ),
                    label=level.get(
                        "label",
                        ""
                    )
                )

            except Exception as error:

                logger.error(
                    "Level error: %s",
                    error
                )

        # =================================
        # PRICE ZONES
        # =================================

        zones = chart_data.get(
            "zones",
            []
        )

        for zone in zones:

            try:

                low = zone.get(
                    "low"
                )

                high = zone.get(
                    "high"
                )

                if low is None or high is None:
                    continue

                ax.axhspan(
                    float(low),
                    float(high),
                    alpha=0.15
                )

            except Exception as error:

                logger.error(
                    "Zone error: %s",
                    error
                )

        # =================================
        # POINTS
        # =================================

        points = chart_data.get(
            "points",
            []
        )

        for point in points:

            try:

                index = point.get(
                    "index"
                )

                price = point.get(
                    "price"
                )

                label = point.get(
                    "label",
                    ""
                )

                if index is None or price is None:
                    continue

                ax.scatter(
                    index,
                    price,
                    s=80,
                    marker="o"
                )

                if label:

                    ax.annotate(
                        label,
                        (
                            index,
                            price
                        ),
                        xytext=(
                            5,
                            5
                        ),
                        textcoords="offset points"
                    )

            except Exception as error:

                logger.error(
                    "Point error: %s",
                    error
                )

        # =================================
        # LINES
        # =================================

        lines = chart_data.get(
            "lines",
            []
        )

        for line in lines:

            try:

                values = line.get(
                    "values"
                )

                if not values:
                    continue

                line_x = list(
                    range(len(values))
                )

                ax.plot(
                    line_x,
                    values,
                    linewidth=line.get(
                        "width",
                        1.5
                    ),
                    label=line.get(
                        "label",
                        ""
                    )
                )

            except Exception as error:

                logger.error(
                    "Line error: %s",
                    error
                )

        # =================================
        # PATTERN CONNECTIONS
        # =================================

        connections = chart_data.get(
            "connections",
            []
        )

        for connection in connections:

            try:

                x_values = connection.get(
                    "x",
                    []
                )

                y_values = connection.get(
                    "y",
                    []
                )

                if not x_values or not y_values:
                    continue

                ax.plot(
                    x_values,
                    y_values,
                    linewidth=2,
                    marker="o",
                    label=connection.get(
                        "label",
                        ""
                    )
                )

            except Exception as error:

                logger.error(
                    "Connection error: %s",
                    error
                )

    # =====================================
    # DATA CHART
    # TVL / NON-CANDLE ANALYSIS
    # =====================================

    def create_data_chart(
        self,
        symbol,
        school,
        result
    ):

        fig, ax = plt.subplots(
            figsize=(12, 6)
        )

        school_name = result.get(
            "school",
            school
        )

        ax.set_title(
            f"{symbol} Analysis - {school_name}"
        )

        chart_data = result.get(
            "chart",
            {}
        )

        values = chart_data.get(
            "values",
            {}
        )

        # =================================
        # DRAW DATA
        # =================================

        if values:

            names = list(
                values.keys()
            )

            numbers = []

            for value in values.values():

                try:
                    numbers.append(
                        float(value)
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    numbers.append(0)

            ax.bar(
                names,
                numbers
            )

        else:

            tvl_value = result.get(
                "tvl",
                0
            )

            change = result.get(
                "tvl_change_30d",
                0
            )

            ax.bar(
                [
                    "TVL",
                    "30d Change"
                ],
                [
                    tvl_value,
                    change
                ]
            )

        ax.grid(
            alpha=0.3
        )

        plt.tight_layout()

        # =================================
        # SAVE
        # =================================

        filename = (
            f"{symbol}_"
            f"{school}_"
            f"{uuid.uuid4().hex}.png"
        )

        path = os.path.join(
            self.chart_dir,
            filename
        )

        plt.savefig(
            path,
            dpi=150,
            bbox_inches="tight"
        )

        plt.close(fig)

        return path        school="analysis",

        analysis_result=None

    ):

        analysis_result = (
            analysis_result or {}
        )

        candles = candles or []


        # =================================
        # DATA ONLY CHART
        # TVL / FUNDAMENTAL / OTHER DATA
        # =================================

        if not candles:

            return self.create_data_chart(

                symbol=symbol,

                school=school,

                result=analysis_result

            )


        # =================================
        # EXTRACT CANDLE DATA
        # =================================

        opens = [

            float(candle["open"])

            for candle in candles

        ]


        highs = [

            float(candle["high"])

            for candle in candles

        ]


        lows = [

            float(candle["low"])

            for candle in candles

        ]


        closes = [

            float(candle["close"])

            for candle in candles

        ]


        volumes = [

            float(
                candle.get(
                    "volume",
                    0
                )
            )

            for candle in candles

        ]


        x = list(
            range(
                len(candles)
            )
        )


        # =================================
        # CREATE FIGURE
        # =================================

        fig, (

            ax_price,

            ax_volume

        ) = plt.subplots(

            2,

            1,

            figsize=(14, 9),

            sharex=True,

            gridspec_kw={

                "height_ratios":

                [

                    4,

                    1

                ]

            }

        )


        # =================================
        # TITLE
        # =================================

        school_title = (

            analysis_result.get(

                "school",

                school

            )

        )


        fig.suptitle(

            f"{symbol} Analysis - "
            f"{school_title}",

            fontsize=20,

            fontweight="bold"

        )


        # =================================
        # DRAW CANDLES
        # =================================

        for i in x:

            open_price = opens[i]

            close_price = closes[i]

            high_price = highs[i]

            low_price = lows[i]


            # =============================
            # CANDLE COLOR
            # =============================

            if close_price >= open_price:

                color = "green"

            else:

                color = "red"


            # =============================
            # WICK
            # =============================

            ax_price.plot(

                [i, i],

                [

                    low_price,

                    high_price

                ],

                color="black",

                linewidth=1

            )


            # =============================
            # BODY
            # =============================

            body_bottom = min(

                open_price,

                close_price

            )


            body_height = abs(

                close_price -

                open_price

            )


            # Prevent invisible candle
            if body_height == 0:

                body_height = max(

                    (
                        high_price -
                        low_price
                    ) * 0.02,

                    0.00000001

                )


            rectangle = Rectangle(

                (

                    i - 0.3,

                    body_bottom

                ),

                0.6,

                body_height,

                facecolor=color,

                edgecolor=color,

                alpha=0.8

            )


            ax_price.add_patch(
                rectangle
            )


        # =================================
        # DRAW VOLUME
        # =================================

        volume_colors = []


        for i in x:

            if closes[i] >= opens[i]:

                volume_colors.append(
                    "green"
                )

            else:

                volume_colors.append(
                    "red"
                )


        ax_volume.bar(

            x,

            volumes,

            color=volume_colors,

            alpha=0.5

        )


        # =================================
        # APPLY SCHOOL ANALYSIS
        # =================================

        self.apply_analysis_overlays(

            ax=ax_price,

            x=x,

            candles=candles,

            result=analysis_result

        )


        # =================================
        # COMMON LEVELS
        # =================================

        self.apply_common_levels(

            ax=ax_price,

            result=analysis_result

        )


        # =================================
        # SIGNAL
        # =================================

        signal = (

            analysis_result.get(

                "signal",

                "WAIT"

            )

        )


        current_price = closes[-1]


        ax_price.text(

            0.02,

            0.95,

            f"Signal: {signal}",

            transform=ax_price.transAxes,

            fontsize=14,

            verticalalignment="top",

            bbox=dict(

                boxstyle="round",

                alpha=0.7

            )

        )


        # Current Price
        ax_price.axhline(

            current_price,

            linestyle=":",

            alpha=0.5,

            label=f"Current {current_price}"

        )


        # =================================
        # CHART STYLE
        # =================================

        ax_price.set_ylabel(
            "Price"
        )


        ax_volume.set_ylabel(
            "Volume"
        )


        ax_price.grid(
            alpha=0.3
        )


        ax_volume.grid(
            alpha=0.3
        )


        # Show legend only if labels exist
        handles, labels = (
            ax_price.get_legend_handles_labels()
        )


        if labels:

            ax_price.legend(
                loc="best"
            )


        # =================================
        # SAVE
        # =================================

        plt.tight_layout()


        filename = (

            f"{symbol}_"
            f"{school}_"
            f"{uuid.uuid4().hex}.png"

        )


        path = os.path.join(

            self.chart_dir,

            filename

        )


        plt.savefig(

            path,

            dpi=150,

            bbox_inches="tight"

        )


        plt.close(
            fig
        )


        return path


    # =====================================
    # COMMON LEVELS
    # =====================================

    def apply_common_levels(

        self,

        ax,

        result

    ):

        support = result.get(
            "support"
        )


        resistance = result.get(
            "resistance"
        )


        target = result.get(
            "target"
        )


        stop_loss = result.get(
            "stop_loss"
        )


        # SUPPORT
        if support is not None:

            ax.axhline(

                support,

                linestyle="--",

                linewidth=1.5,

                label=f"Support {support}"

            )


        # RESISTANCE
        if resistance is not None:

            ax.axhline(

                resistance,

                linestyle="--",

                linewidth=1.5,

                label=f"Resistance {resistance}"

            )


        # TARGET
        if target is not None:

            ax.axhline(

                target,

                linestyle=":",

                linewidth=2,

                label=f"Target {target}"

            )


        # STOP LOSS
        if stop_loss is not None:

            ax.axhline(

                stop_loss,

                linestyle=":",

                linewidth=2,

                label=f"Stop Loss {stop_loss}"

            )


    # =====================================
    # ANALYSIS OVERLAYS
    # =====================================

    def apply_analysis_overlays(

        self,

        ax,

        x,

        candles,

        result

    ):

        chart_data = result.get(
            "chart"
        )


        if not chart_data:

            return


        # =================================
        # HORIZONTAL LEVELS
        # =================================

        levels = chart_data.get(

            "levels",

            []

        )


        for level in levels:

            try:

                price = level.get(
                    "price"
                )


                if price is None:

                    continue


                ax.axhline(

                    price,

                    linestyle=level.get(

                        "style",

                        "--"

                    ),

                    linewidth=level.get(

                        "width",

                        1.5

                    ),

                    label=level.get(

                        "label",

                        ""

                    )

                )


            except Exception as error:

                logger.exception(

                    f"Level chart error: "
                    f"{error}"

                )


        # =================================
        # ZONES
        # =================================

        zones = chart_data.get(

            "zones",

            []

        )


        for zone in zones:

            try:

                low = zone.get(
                    "low"
                )


                high = zone.get(
                    "high"
                )


                if (

                    low is None

                    or

                    high is None

                ):

                    continue


                ax.axhspan(

                    low,

                    high,

                    alpha=0.15

                )


            except Exception as error:

                logger.exception(

                    f"Zone chart error: "
                    f"{error}"

                )


        # =================================
        # POINTS
        # =================================

        points = chart_data.get(

            "points",

            []

        )


        for point in points:

            try:

                index = point.get(
                    "index"
                )


                price = point.get(
                    "price"
                )


                label = point.get(
                    "label",
                    ""
                )


                if (

                    index is None

                    or

                    price is None

                ):

                    continue


                # Make sure index is valid
                if index < 0:

                    continue


                if index >= len(x):

                    continue


                ax.scatter(

                    index,

                    price,

                    s=80,

                    marker="o"

                )


                if label:

                    ax.annotate(

                        label,

                        (

                            index,

                            price

                        ),

                        xytext=(

                            5,

                            5

                        ),

                        textcoords="offset points"

                    )


            except Exception as error:

                logger.exception(

                    f"Point chart error: "
                    f"{error}"

                )


        # =================================
        # CUSTOM LINES
        # =================================

        lines = chart_data.get(

            "lines",

            []

        )


        for line in lines:

            try:

                values = line.get(
                    "values"
                )


                if not values:

                    continue


                # Align line with latest candles
                start_index = max(

                    0,

                    len(x) -

                    len(values)

                )


                line_x = list(

                    range(

                        start_index,

                        start_index +

                        len(values)

                    )

                )


                ax.plot(

                    line_x,

                    values,

                    linewidth=line.get(

                        "width",

                        1.5

                    ),

                    label=line.get(

                        "label",

                        ""

                    )

                )


            except Exception as error:

                logger.exception(

                    f"Line chart error: "
                    f"{error}"

                )


        # =================================
        # PATTERN CONNECTIONS
        # =================================

        connections = chart_data.get(

            "connections",

            []

        )


        for connection in connections:

            try:

                x_values = connection.get(

                    "x",

                    []

                )


                y_values = connection.get(

                    "y",

                    []

                )


                if not x_values:

                    continue


                if not y_values:

                    continue


                if (

                    len(x_values)

                    !=

                    len(y_values)

                ):

                    continue


                ax.plot(

                    x_values,

                    y_values,

                    linewidth=2,

                    marker="o",

                    label=connection.get(

                        "label",

                        ""

                    )

                )


            except Exception as error:

                logger.exception(

                    f"Connection chart error: "
                    f"{error}"

                )


    # =====================================
    # DATA CHART
    # TVL / FUNDAMENTAL DATA
    # =====================================

    def create_data_chart(

        self,

        symbol,

        school,

        result

    ):

        fig, ax = plt.subplots(

            figsize=(12, 6)

        )


        school_name = result.get(

            "school",

            school

        )


        chart_data = result.get(

            "chart",

            {}

        )


        title = chart_data.get(

            "title",

            f"{symbol} Analysis - "
            f"{school_name}"

        )


        ax.set_title(

            title,

            fontsize=18,

            fontweight="bold"

        )


        # =================================
        # DICTIONARY VALUES
        # =================================

        values = chart_data.get(
            "values"
        )


        if isinstance(
            values,
            dict
        ) and values:

            names = list(
                values.keys()
            )


            numbers = []


            for value in values.values():

                try:

                    numbers.append(
                        float(value)
                    )

                except (

                    TypeError,

                    ValueError

                ):

                    numbers.append(
                        0
                    )


        # =================================
        # LIST VALUES + LABELS
        # =================================

        elif isinstance(
            values,
            list
        ):

            names = chart_data.get(

                "labels",

                []

            )


            numbers = []


            for value in values:

                try:

                    numbers.append(
                        float(value)
                    )

                except (

                    TypeError,

                    ValueError

                ):

                    numbers.append(
                        0
                    )


            if not names:

                names = [

                    f"Value {i + 1}"

                    for i in range(

                        len(numbers)

                    )

                ]


        # =================================
        # FALLBACK
        # =================================

        else:

            names = [

                "TVL",

                "30d Change"

            ]


            numbers = [

                float(

                    result.get(

                        "tvl",

                        0

                    )

                ),

                float(

                    result.get(

                        "tvl_change_30d",

                        0

                    )

                )

            ]


        # =================================
        # DRAW BARS
        # =================================

        bars = ax.bar(

            names,

            numbers

        )


        # =================================
        # SHOW VALUES ABOVE BARS
        # =================================

        for bar, value in zip(

            bars,

            numbers

        ):

            height = bar.get_height()


            ax.annotate(

                f"{value:.2f}",

                xy=(

                    bar.get_x()

                    +

                    bar.get_width() / 2,

                    height

                ),

                xytext=(

                    0,

                    5

                ),

                textcoords="offset points",

                ha="center",

                va="bottom"

            )


        ax.grid(

            alpha=0.3,

            axis="y"

        )


        # =================================
        # SAVE
        # =================================

        filename = (

            f"{symbol}_"
            f"{school}_"
            f"{uuid.uuid4().hex}.png"

        )


        path = os.path.join(

            self.chart_dir,

            filename

        )


        plt.tight_layout()


        plt.savefig(

            path,

            dpi=150,

            bbox_inches="tight"

        )


        plt.close(
            fig
        )


        return path        symbol,

        candles,

        school,

        analysis_result=None

    ):


        analysis_result = (
            analysis_result or {}
        )


        # =============================
        # TVL WITHOUT CANDLES
        # =============================

        if not candles:

            return self.create_data_chart(

                symbol,

                school,

                analysis_result

            )


        # =============================
        # EXTRACT CANDLE DATA
        # =============================

        opens = [

            float(
                candle["open"]
            )

            for candle in candles

        ]


        highs = [

            float(
                candle["high"]
            )

            for candle in candles

        ]


        lows = [

            float(
                candle["low"]
            )

            for candle in candles

        ]


        closes = [

            float(
                candle["close"]
            )

            for candle in candles

        ]


        volumes = [

            float(
                candle.get(

                    "volume",

                    0

                )
            )

            for candle in candles

        ]


        x = list(

            range(

                len(candles)

            )

        )


        # =============================
        # FIGURE
        # =============================

        fig, (

            ax_price,

            ax_volume

        ) = plt.subplots(

            2,

            1,

            figsize=(14, 9),

            sharex=True,

            gridspec_kw={

                "height_ratios":

                [

                    4,

                    1

                ]

            }

        )


        # =============================
        # TITLE
        # =============================

        school_title = (

            analysis_result.get(

                "school",

                school.title()

            )

        )


        fig.suptitle(

            f"{symbol} Analysis - "

            f"{school_title}",

            fontsize=20,

            fontweight="bold"

        )


        # =============================
        # DRAW CANDLES
        # =============================

        for i in x:


            open_price = opens[i]

            close_price = closes[i]

            high_price = highs[i]

            low_price = lows[i]


            # Green / Red
            if close_price >= open_price:

                color = "green"

            else:

                color = "red"


            # Wick
            ax_price.plot(

                [i, i],

                [

                    low_price,

                    high_price

                ],

                color="black",

                linewidth=1

            )


            # Body
            body_bottom = min(

                open_price,

                close_price

            )


            body_height = abs(

                close_price -

                open_price

            )


            # Avoid zero body
            if body_height == 0:

                body_height = (

                    high_price -

                    low_price

                ) * 0.02


            rectangle = Rectangle(

                (

                    i - 0.3,

                    body_bottom

                ),

                0.6,

                body_height,

                facecolor=color,

                edgecolor=color,

                alpha=0.8

            )


            ax_price.add_patch(

                rectangle

            )


        # =============================
        # VOLUME
        # =============================

        volume_colors = []


        for i in x:


            if closes[i] >= opens[i]:

                volume_colors.append(

                    "green"

                )

            else:

                volume_colors.append(

                    "red"

                )


        ax_volume.bar(

            x,

            volumes,

            color=volume_colors,

            alpha=0.5

        )


        # =================================
        # GENERIC RESULT OVERLAYS
        # =================================

        self.apply_analysis_overlays(

            ax_price,

            x,

            candles,

            analysis_result

        )


        # =================================
        # CLASSIC FALLBACK
        # =================================

        self.apply_common_levels(

            ax_price,

            analysis_result

        )


        # =================================
        # SIGNAL
        # =================================

        signal = (

            analysis_result.get(

                "signal",

                "WAIT"

            )

        )


        current_price = closes[-1]


        ax_price.text(

            0.02,

            0.95,

            f"Signal: {signal}",

            transform=ax_price.transAxes,

            fontsize=14,

            verticalalignment="top",

            bbox=dict(

                boxstyle="round",

                alpha=0.7

            )

        )


        ax_price.axhline(

            current_price,

            linestyle=":",

            alpha=0.5

        )


        # =================================
        # STYLE
        # =================================

        ax_price.set_ylabel(

            "Price"

        )


        ax_volume.set_ylabel(

            "Volume"

        )


        ax_price.grid(

            alpha=0.3

        )


        ax_volume.grid(

            alpha=0.3

        )


        ax_price.legend(

            loc="upper left"

        )


        plt.tight_layout()


        # =================================
        # SAVE
        # =================================

        filename = (

            f"{symbol}_"

            f"{school}_"

            f"{uuid.uuid4().hex}.png"

        )


        path = os.path.join(

            self.chart_dir,

            filename

        )


        plt.savefig(

            path,

            dpi=150,

            bbox_inches="tight"

        )


        plt.close()


        return path


    # =====================================
    # COMMON LEVELS
    # =====================================

    def apply_common_levels(

        self,

        ax,

        result

    ):


        support = result.get(

            "support"

        )


        resistance = result.get(

            "resistance"

        )


        # SUPPORT
        if support is not None:


            ax.axhline(

                support,

                linestyle="--",

                linewidth=1.5,

                label=f"Support {support}"

            )


        # RESISTANCE
        if resistance is not None:


            ax.axhline(

                resistance,

                linestyle="--",

                linewidth=1.5,

                label=f"Resistance {resistance}"

            )


        # TARGET
        target = result.get(

            "target"

        )


        if target is not None:


            ax.axhline(

                target,

                linestyle=":",

                linewidth=2,

                label=f"Target {target}"

            )


        # STOP LOSS
        stop_loss = result.get(

            "stop_loss"

        )


        if stop_loss is not None:


            ax.axhline(

                stop_loss,

                linestyle=":",

                linewidth=2,

                label=f"Stop Loss {stop_loss}"

            )


    # =====================================
    # GENERIC OVERLAYS
    # =====================================

    def apply_analysis_overlays(

        self,

        ax,

        x,

        candles,

        result

    ):


        chart_data = (

            result.get(

                "chart",

                {}

            )

        )


        # =============================
        # HORIZONTAL LEVELS
        # =============================

        levels = (

            chart_data.get(

                "levels",

                []

            )

        )


        for level in levels:


            try:


                ax.axhline(

                    level["price"],

                    linestyle=level.get(

                        "style",

                        "--"

                    ),

                    linewidth=level.get(

                        "width",

                        1.5

                    ),

                    label=level.get(

                        "label",

                        ""

                    )

                )


            except Exception as error:


                logger.error(

                    f"Level error: {error}"

                )


        # =============================
        # PRICE ZONES
        # =============================

        zones = (

            chart_data.get(

                "zones",

                []

            )

        )


        for zone in zones:


            try:


                low = zone.get(

                    "low"

                )


                high = zone.get(

                    "high"

                )


                if (

                    low is None

                    or

                    high is None

                ):

                    continue


                ax.axhspan(

                    low,

                    high,

                    alpha=0.15

                )


            except Exception as error:


                logger.error(

                    f"Zone error: {error}"

                )


        # =============================
        # POINTS
        # =============================

        points = (

            chart_data.get(

                "points",

                []

            )

        )


        for point in points:


            try:


                index = point.get(

                    "index"

                )


                price = point.get(

                    "price"

                )


                label = point.get(

                    "label",

                    ""

                )


                if (

                    index is None

                    or

                    price is None

                ):

                    continue


                ax.scatter(

                    index,

                    price,

                    s=80,

                    marker="o"

                )


                if label:


                    ax.annotate(

                        label,

                        (

                            index,

                            price

                        ),

                        xytext=(

                            5,

                            5

                        ),

                        textcoords="offset points"

                    )


            except Exception as error:


                logger.error(

                    f"Point error: {error}"

                )


        # =============================
        # LINES
        # =============================

        lines = (

            chart_data.get(

                "lines",

                []

            )

        )


        for line in lines:


            try:


                values = line.get(

                    "values"

                )


                if not values:

                    continue


                line_x = list(

                    range(

                        len(values)

                    )

                )


                ax.plot(

                    line_x,

                    values,

                    linewidth=line.get(

                        "width",

                        1.5

                    ),

                    label=line.get(

                        "label",

                        ""

                    )

                )


            except Exception as error:


                logger.error(

                    f"Line error: {error}"

                )


        # =============================
        # PATTERN CONNECTIONS
        # =============================

        connections = (

            chart_data.get(

                "connections",

                []

            )

        )


        for connection in connections:


            try:


                x_values = connection.get(

                    "x",

                    []

                )


                y_values = connection.get(

                    "y",

                    []

                )


                if (

                    not x_values

                    or

                    not y_values

                ):

                    continue


                ax.plot(

                    x_values,

                    y_values,

                    linewidth=2,

                    marker="o",

                    label=connection.get(

                        "label",

                        ""

                    )

                )


            except Exception as error:


                logger.error(

                    f"Connection error: {error}"

                )


    # =====================================
    # DATA CHART
    # FOR TVL / OTHER NON-CANDLE DATA
    # =====================================

    def create_data_chart(

        self,

        symbol,

        school,

        result

    ):


        fig, ax = plt.subplots(

            figsize=(12, 6)

        )


        school_name = (

            result.get(

                "school",

                school

            )

        )


        ax.set_title(

            f"{symbol} Analysis - "

            f"{school_name}"

        )


        chart_data = result.get(

            "chart",

            {}

        )


        values = chart_data.get(

            "values",

            {}

        )


        if values:


            names = list(

                values.keys()

            )


            numbers = list(

                values.values()

            )


            ax.bar(

                names,

                numbers

            )


        else:


            # Fallback TVL
            tvl_value = result.get(

                "tvl",

                0

            )


            change = result.get(

                "tvl_change_30d",

                0

            )


            ax.bar(

                [

                    "TVL",

                    "30d Change"

                ],

                [

                    tvl_value,

                    change

                ]

            )


        path = os.path.join(

            self.chart_dir,

            f"{symbol}_{school}_"

            f"{uuid.uuid4().hex}.png"

        )


        plt.tight_layout()

        plt.savefig(

            path,

            dpi=150

        )


        plt.close()


        return path
