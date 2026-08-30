import pandas as pd
from typing import Dict, Any

def analyze_volume_profile(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """Volume Profile تقريبي"""
    if len(df) < 40 or "volume" not in df.columns:
        return {"signal": "insufficient_data", "reason": "بيانات غير كافية"}

    # نقطة تحكم تقريبية (POC)
    df = df.copy()
    df["typical"] = (df["high"] + df["low"] + df["close"]) / 3
    # تبسيط: أعلى حجم في آخر 40 شمعة
    max_vol_idx = df["volume"].iloc[-40:].idxmax()
    poc_price = df.loc[max_vol_idx, "typical"]
    last_price = df["close"].iloc[-1]

    signal = "neutral"
    reasons = []

    if last_price > poc_price * 1.01:
        signal = "above_poc"
        reasons.append("السعر فوق نقطة التحكم (POC)")
    elif last_price < poc_price * 0.99:
        signal = "below_poc"
        reasons.append("السعر تحت نقطة التحكم (POC)")

    return {
        "school": "Volume Profile",
        "symbol": symbol,
        "signal": signal,
        "reasons": reasons,
        "poc": float(poc_price),
        "last_price": float(last_price)
    }
