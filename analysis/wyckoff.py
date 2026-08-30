import pandas as pd
from typing import Dict, Any

def analyze_wyckoff(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """Wyckoff Method - منطق مختلف كلياً"""
    if len(df) < 60:
        return {"signal": "insufficient_data", "reason": "بيانات غير كافية"}

    volume = df["volume"] if "volume" in df.columns else pd.Series([1]*len(df))
    close = df["close"]

    avg_vol = volume.rolling(20).mean().iloc[-1]
    last_vol = volume.iloc[-1]
    price_change = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20]

    signal = "neutral"
    reasons = []

    if last_vol > avg_vol * 1.5 and price_change > 0.03:
        signal = "accumulation"
        reasons.append("حجم مرتفع مع صعود → تراكم محتمل")
    elif last_vol > avg_vol * 1.5 and price_change < -0.03:
        signal = "distribution"
        reasons.append("حجم مرتفع مع هبوط → توزيع محتمل")

    return {
        "school": "Wyckoff",
        "symbol": symbol,
        "signal": signal,
        "reasons": reasons,
        "last_price": float(close.iloc[-1])
    }
