import pandas as pd
from typing import Dict, Any

def analyze_elliott(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """Elliott Wave - تقريب بسيط جداً (ليس تحليلاً دقيقاً)"""
    if len(df) < 80:
        return {"signal": "insufficient_data", "reason": "بيانات غير كافية"}

    closes = df["close"].values
    # تقريب بدائي للموجات
    mid = len(closes) // 2
    first_half_trend = closes[mid] - closes[0]
    second_half_trend = closes[-1] - closes[mid]

    signal = "neutral"
    reasons = []

    if first_half_trend > 0 and second_half_trend > 0:
        signal = "impulse_up"
        reasons.append("اتجاه صاعد محتمل (موجة دافعة)")
    elif first_half_trend < 0 and second_half_trend < 0:
        signal = "impulse_down"
        reasons.append("اتجاه هابط محتمل")

    return {
        "school": "Elliott Wave",
        "symbol": symbol,
        "signal": signal,
        "reasons": reasons,
        "last_price": float(closes[-1])
    }
