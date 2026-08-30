import pandas as pd
from typing import Dict, Any

def analyze_price_action(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """تحليل Price Action خاص بكل عملة"""
    if len(df) < 50:
        return {"signal": "insufficient_data", "reason": "بيانات غير كافية"}

    last_close = df["close"].iloc[-1]
    prev_close = df["close"].iloc[-2]
    high_20 = df["high"].rolling(20).max().iloc[-1]
    low_20 = df["low"].rolling(20).min().iloc[-1]

    signal = "neutral"
    reason = []

    if last_close > high_20:
        signal = "bullish_breakout"
        reason.append("كسر قمة 20 شمعة")
    elif last_close < low_20:
        signal = "bearish_breakdown"
        reason.append("كسر قاع 20 شمعة")

    if last_close > prev_close * 1.02:
        reason.append("شمعة صاعدة قوية")
    elif last_close < prev_close * 0.98:
        reason.append("شمعة هابطة قوية")

    return {
        "school": "Price Action",
        "symbol": symbol,
        "signal": signal,
        "reasons": reason,
        "last_price": float(last_close)
    }
