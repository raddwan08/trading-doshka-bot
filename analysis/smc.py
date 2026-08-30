import pandas as pd
from typing import Dict, Any

def analyze_smc(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """Smart Money Concepts - دوال مختلفة تماماً عن Price Action"""
    if len(df) < 100:
        return {"signal": "insufficient_data", "reason": "بيانات غير كافية"}

    # Order Block بسيط
    recent_high = df["high"].iloc[-20:].max()
    recent_low = df["low"].iloc[-20:].min()
    last_close = df["close"].iloc[-1]

    signal = "neutral"
    reasons = []

    # Fair Value Gap تقريبي
    if df["low"].iloc[-1] > df["high"].iloc[-3]:
        reasons.append("FVG صاعد محتمل")
        signal = "bullish_fvg"
    elif df["high"].iloc[-1] < df["low"].iloc[-3]:
        reasons.append("FVG هابط محتمل")
        signal = "bearish_fvg"

    if last_close > recent_high * 0.98:
        reasons.append("قرب Order Block علوي")
    if last_close < recent_low * 1.02:
        reasons.append("قرب Order Block سفلي")

    return {
        "school": "Smart Money Concepts",
        "symbol": symbol,
        "signal": signal,
        "reasons": reasons,
        "last_price": float(last_close)
    }
