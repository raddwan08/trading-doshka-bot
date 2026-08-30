import pandas as pd
import numpy as np
from typing import Dict, List

class IchimokuAnalyzer:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.signals = []
    
    def analyze(self) -> Dict:
        """تحليل إيشيموكو"""
        signals = []
        
        # حساب مكونات إيشيموكو
        tenkan_sen = self.calculate_tenkan_sen()
        kijun_sen = self.calculate_kijun_sen()
        senkou_span_a = self.calculate_senkou_span_a(tenkan_sen, kijun_sen)
        senkou_span_b = self.calculate_senkou_span_b()
        
        current_price = self.data['close'].iloc[-1]
        
        # تحليل Tenkan-Kijun Cross
        if tenkan_sen.iloc[-1] > kijun_sen.iloc[-1] and tenkan_sen.iloc[-2] <= kijun_sen.iloc[-2]:
            signals.append("تقاطع Tenkan-Kijun صاعد - إشارة شراء")
            cross_signal = "شراء"
        elif tenkan_sen.iloc[-1] < kijun_sen.iloc[-1] and tenkan_sen.iloc[-2] >= kijun_sen.iloc[-2]:
            signals.append("تقاطع Tenkan-Kijun هابط - إشارة بيع")
            cross_signal = "بيع"
        else:
            signals.append("لا يوجد تقاطع حديث")
            cross_signal = "محايد"
        
        # تحليل Kumo (السحابة)
        if current_price > senkou_span_a.iloc[-1] and current_price > senkou_span_b.iloc[-1]:
            signals.append("السعر فوق السحابة - اتجاه صاعد")
            cloud_signal = "صاعد"
        elif current_price < senkou_span_a.iloc[-1] and current_price < senkou_span_b.iloc[-1]:
            signals.append("السعر تحت السحابة - اتجاه هابط")
            cloud_signal = "هابط"
        else:
            signals.append("السعر داخل السحابة - منطقة تذبذب")
            cloud_signal = "محايد"
        
        # Chikou Span
        chikou_span = self.data['close'].shift(-26)
        if len(chikou_span.dropna()) > 0:
            chikou_current = chikou_span.iloc[-26] if len(chikou_span) >= 26 else None
            if chikou_current:
                if chikou_current > self.data['close'].iloc[-26]:
                    signals.append("Chikou Span فوق السعر - تأكيد صاعد")
                else:
                    signals.append("Chikou Span تحت السعر - تأكيد هابط")
        
        # الإشارة النهائية
        if cross_signal == "شراء" and cloud_signal == "صاعد":
            signal = "شراء"
        elif cross_signal == "بيع" and cloud_signal == "هابط":
            signal = "بيع"
        else:
            signal = "محايد"
        
        return {
            "school": "Ichimoku",
            "signal": signal,
            "tenkan_sen": round(tenkan_sen.iloc[-1], 2),
            "kijun_sen": round(kijun_sen.iloc[-1], 2),
            "cloud_status": cloud_signal,
            "confidence": self.calculate_confidence(cross_signal, cloud_signal),
            "details": signals
        }
    
    def calculate_tenkan_sen(self) -> pd.Series:
        """حساب Tenkan-sen (خط التحويل)"""
        high = self.data['high'].rolling(window=9).max()
        low = self.data['low'].rolling(window=9).min()
        return (high + low) / 2
    
    def calculate_kijun_sen(self) -> pd.Series:
        """حساب Kijun-sen (خط الأساس)"""
        high = self.data['high'].rolling(window=26).max()
        low = self.data['low'].rolling(window=26).min()
        return (high + low) / 2
    
    def calculate_senkou_span_a(self, tenkan_sen: pd.Series, kijun_sen: pd.Series) -> pd.Series:
        """حساب Senkou Span A"""
        return ((tenkan_sen + kijun_sen) / 2).shift(26)
    
    def calculate_senkou_span_b(self) -> pd.Series:
        """حساب Senkou Span B"""
        high = self.data['high'].rolling(window=52).max()
        low = self.data['low'].rolling(window=52).min()
        return ((high + low) / 2).shift(26)
    
    def calculate_confidence(self, cross_signal: str, cloud_signal: str) -> int:
        confidence = 50
        
        if cross_signal != "محايد":
            confidence += 15
        if cloud_signal != "محايد":
            confidence += 15
        if cross_signal == "شراء" and cloud_signal == "صاعد":
            confidence += 20
        elif cross_signal == "بيع" and cloud_signal == "هابط":
            confidence += 20
        
        return min(90, confidence)
