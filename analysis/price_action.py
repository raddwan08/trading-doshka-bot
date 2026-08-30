import pandas as pd
import numpy as np
from typing import Dict, List

class PriceActionAnalyzer:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.signals = []
    
    def analyze(self) -> Dict:
        """تحليل حركة السعر الكلاسيكي"""
        signals = []
        
        # تحديد الاتجاه العام
        sma_20 = self.data['close'].rolling(window=20).mean()
        sma_50 = self.data['close'].rolling(window=50).mean()
        
        current_price = self.data['close'].iloc[-1]
        
        if sma_20.iloc[-1] > sma_50.iloc[-1]:
            trend = "صاعد"
            signals.append("السعر فوق المتوسطات المتحركة - اتجاه صاعد")
        elif sma_20.iloc[-1] < sma_50.iloc[-1]:
            trend = "هابط"
            signals.append("السعر تحت المتوسطات المتحركة - اتجاه هابط")
        else:
            trend = "عرضي"
            signals.append("السوق في حالة تذبذب")
        
        # تحديد الدعم والمقاومة
        recent_lows = self.data['low'].tail(20).min()
        recent_highs = self.data['high'].tail(20).max()
        
        signals.append(f"مستوى الدعم: {recent_lows:.2f}")
        signals.append(f"مستوى المقاومة: {recent_highs:.2f}")
        
        # نمط الشموع
        last_candle = self.data.iloc[-1]
        prev_candle = self.data.iloc[-2]
        
        if last_candle['close'] > last_candle['open']:
            candle_type = "شمعة صاعدة"
            if last_candle['close'] > prev_candle['high']:
                signals.append("اختراق صاعد للقمة السابقة - إشارة شراء قوية")
        else:
            candle_type = "شمعة هابطة"
            if last_candle['close'] < prev_candle['low']:
                signals.append("كسر هابط للقاع السابق - إشارة بيع قوية")
        
        signals.append(f"نوع الشمعة الأخيرة: {candle_type}")
        
        # حساب RSI
        rsi = self.calculate_rsi()
        if rsi < 30:
            signal = "شراء"
            signals.append(f"RSI = {rsi:.2f} - منطقة تشبع بيعي")
        elif rsi > 70:
            signal = "بيع"
            signals.append(f"RSI = {rsi:.2f} - منطقة تشبع شرائي")
        else:
            signal = "محايد"
            signals.append(f"RSI = {rsi:.2f} - منطقة محايدة")
        
        return {
            "school": "Price Action",
            "trend": trend,
            "signal": signal,
            "confidence": self.calculate_confidence(signals),
            "details": signals
        }
    
    def calculate_rsi(self, period=14) -> float:
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    
    def calculate_confidence(self, signals: List[str]) -> int:
        # حساب نسبة الثقة بناءً على عدد الإشارات المتوافقة
        return min(90, len(signals) * 15)
