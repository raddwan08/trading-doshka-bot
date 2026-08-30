import pandas as pd
import numpy as np
from typing import Dict, List

class FibonacciAnalyzer:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.signals = []
    
    def analyze(self) -> Dict:
        """تحليل فيبوناتشي"""
        signals = []
        
        # تحديد القمة والقاع الرئيسيين
        recent_data = self.data.tail(50)
        swing_high = recent_data['high'].max()
        swing_low = recent_data['low'].min()
        current_price = recent_data['close'].iloc[-1]
        
        # حساب مستويات فيبوناتشي
        diff = swing_high - swing_low
        levels = {
            "0.0%": swing_high,
            "23.6%": swing_high - 0.236 * diff,
            "38.2%": swing_high - 0.382 * diff,
            "50.0%": swing_high - 0.5 * diff,
            "61.8%": swing_high - 0.618 * diff,
            "78.6%": swing_high - 0.786 * diff,
            "100.0%": swing_low
        }
        
        # تحديد أقرب مستوى
        closest_level = self.find_closest_level(current_price, levels)
        signals.append(f"أقرب مستوى فيبوناتشي: {closest_level}")
        
        # تحليل التصحيح
        retracement = self.calculate_retracement(current_price, swing_high, swing_low)
        signals.append(f"نسبة التصحيح: {retracement}%")
        
        # تحديد مناطق الدعم والمقاومة
        supports = [levels["38.2%"], levels["50.0%"], levels["61.8%"]]
        resistances = [levels["23.6%"], levels["38.2%"]]
        
        # الإشارة
        if retracement < 38.2:
            signal = "شراء"
            signals.append("تصحيح ضحل - استمرار الاتجاه الصاعد")
        elif retracement > 61.8:
            signal = "بيع"
            signals.append("تصحيح عميق - احتمال انعكاس الاتجاه")
        else:
            signal = "محايد"
            signals.append("منطقة تصحيح طبيعية")
        
        # أهداف فيبوناتشي
        if signal == "شراء":
            target1 = current_price + (swing_high - swing_low) * 0.618
            target2 = current_price + (swing_high - swing_low) * 1.0
            signals.append(f"أهداف: T1=${target1:.2f}, T2=${target2:.2f}")
        elif signal == "بيع":
            target1 = current_price - (swing_high - swing_low) * 0.618
            target2 = current_price - (swing_high - swing_low) * 1.0
            signals.append(f"أهداف: T1=${target1:.2f}, T2=${target2:.2f}")
        
        return {
            "school": "Fibonacci",
            "signal": signal,
            "retracement": retracement,
            "closest_level": closest_level,
            "levels": levels,
            "confidence": self.calculate_confidence(retracement),
            "details": signals
        }
    
    def find_closest_level(self, price: float, levels: Dict) -> str:
        """البحث عن أقرب مستوى"""
        closest = None
        min_distance = float('inf')
        
        for level_name, level_price in levels.items():
            distance = abs(price - level_price)
            if distance < min_distance:
                min_distance = distance
                closest = f"{level_name} (${level_price:.2f})"
        
        return closest
    
    def calculate_retracement(self, current_price: float, swing_high: float, swing_low: float) -> float:
        """حساب نسبة التصحيح"""
        if swing_high == swing_low:
            return 0.0
        
        retracement = ((swing_high - current_price) / (swing_high - swing_low)) * 100
        return round(retracement, 2)
    
    def calculate_confidence(self, retracement: float) -> int:
        if 38.2 <= retracement <= 61.8:
            return 75
        elif retracement < 23.6:
            return 70
        else:
            return 60
