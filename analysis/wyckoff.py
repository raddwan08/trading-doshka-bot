import pandas as pd
import numpy as np
from typing import Dict, List

class WyckoffAnalyzer:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.signals = []
    
    def analyze(self) -> Dict:
        """تحليل وايكوف"""
        signals = []
        
        # تحديد المرحلة
        phase = self.identify_phase()
        signals.append(f"مرحلة وايكوف الحالية: {phase}")
        
        # تحليل العرض والطلب
        volume = self.data['volume'].tail(20)
        price_change = self.data['close'].pct_change().tail(20)
        
        # حساب قوة العرض والطلب
        buying_pressure = (volume * (price_change > 0)).sum()
        selling_pressure = (volume * (price_change < 0)).sum()
        
        if buying_pressure > selling_pressure * 1.2:
            signals.append("ضغط شرائي أقوى من البيعي")
            pressure = "شرائي"
        elif selling_pressure > buying_pressure * 1.2:
            signals.append("ضغط بيعي أقوى من الشرائي")
            pressure = "بيعي"
        else:
            signals.append("توازن بين العرض والطلب")
            pressure = "متوازن"
        
        # تحديد Accumulation/Distribution
        accumulation = self.check_accumulation()
        if accumulation:
            signals.append("نمط Accumulation محتمل")
        else:
            distribution = self.check_distribution()
            if distribution:
                signals.append("نمط Distribution محتمل")
        
        # Spring/Upthrust
        spring = self.check_spring()
        if spring:
            signals.append("Spring detected - فرصة شراء محتملة")
            signal = "شراء"
        else:
            upthrust = self.check_upthrust()
            if upthrust:
                signals.append("Upthrust detected - فرصة بيع محتملة")
                signal = "بيع"
            else:
                signal = "محايد"
        
        return {
            "school": "Wyckoff",
            "phase": phase,
            "pressure": pressure,
            "signal": signal,
            "confidence": self.calculate_confidence(phase, pressure),
            "details": signals
        }
    
    def identify_phase(self) -> str:
        """تحديد مرحلة وايكوف"""
        recent_data = self.data.tail(30)
        price_range = recent_data['high'].max() - recent_data['low'].min()
        current_price = recent_data['close'].iloc[-1]
        
        # حساب موقع السعر ضمن النطاق
        position = (current_price - recent_data['low'].min()) / price_range if price_range > 0 else 0.5
        
        volume_trend = recent_data['volume'].rolling(window=10).mean()
        price_trend = recent_data['close'].rolling(window=10).mean()
        
        if position < 0.3 and volume_trend.iloc[-1] > volume_trend.mean():
            return "Accumulation"
        elif position > 0.7 and volume_trend.iloc[-1] < volume_trend.mean():
            return "Distribution"
        elif price_trend.iloc[-1] > price_trend.iloc[-5]:
            return "Markup"
        elif price_trend.iloc[-1] < price_trend.iloc[-5]:
            return "Markdown"
        else:
            return "Range"
    
    def check_accumulation(self) -> bool:
        """التحقق من وجود Accumulation"""
        recent_lows = self.data['low'].tail(15)
        recent_volumes = self.data['volume'].tail(15)
        
        # البحث عن قيعان متساوية مع انخفاض في الحجم
        low_std = recent_lows.std()
        volume_decreasing = recent_volumes.iloc[-1] < recent_volumes.iloc[0] * 0.8
        
        return low_std < recent_lows.mean() * 0.02 and volume_decreasing
    
    def check_distribution(self) -> bool:
        """التحقق من وجود Distribution"""
        recent_highs = self.data['high'].tail(15)
        recent_volumes = self.data['volume'].tail(15)
        
        high_std = recent_highs.std()
        volume_decreasing = recent_volumes.iloc[-1] < recent_volumes.iloc[0] * 0.8
        
        return high_std < recent_highs.mean() * 0.02 and volume_decreasing
    
    def check_spring(self) -> bool:
        """التحقق من Spring"""
        recent_data = self.data.tail(10)
        support = recent_data['low'].tail(5).min()
        last_candle = recent_data.iloc[-1]
        
        # Spring: كسر الدعم ثم العودة فوقه
        if last_candle['low'] < support and last_candle['close'] > support:
            return True
        return False
    
    def check_upthrust(self) -> bool:
        """التحقق من Upthrust"""
        recent_data = self.data.tail(10)
        resistance = recent_data['high'].tail(5).max()
        last_candle = recent_data.iloc[-1]
        
        # Upthrust: كسر المقاومة ثم العودة تحتها
        if last_candle['high'] > resistance and last_candle['close'] < resistance:
            return True
        return False
    
    def calculate_confidence(self, phase: str, pressure: str) -> int:
        confidence = 40
        
        if phase in ["Accumulation", "Markup"] and pressure == "شرائي":
            confidence += 30
        elif phase in ["Distribution", "Markdown"] and pressure == "بيعي":
            confidence += 30
        elif pressure != "متوازن":
            confidence += 15
        
        return min(85, confidence)
