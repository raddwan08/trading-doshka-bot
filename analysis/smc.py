import pandas as pd
import numpy as np
from typing import Dict, List

class SMCAnalyzer:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.signals = []
    
    def analyze(self) -> Dict:
        """تحليل Smart Money Concepts"""
        signals = []
        
        # تحديد مناطق العرض والطلب
        volume = self.data['volume']
        price = self.data['close']
        
        # البحث عن مناطق السيولة
        avg_volume = volume.rolling(window=20).mean()
        current_volume = volume.iloc[-1]
        
        if current_volume > avg_volume.iloc[-1] * 1.5:
            signals.append("حجم تداول مرتفع - دخول مؤسسي محتمل")
            volume_signal = "نشاط مؤسسي"
        else:
            signals.append("حجم تداول عادي")
            volume_signal = "نشاط عادي"
        
        # تحديد مناطق Order Blocks
        recent_data = self.data.tail(30)
        potential_ob = self.find_order_blocks(recent_data)
        
        if potential_ob:
            signals.append(f"منطقة Order Block عند: {potential_ob['price']:.2f}")
        
        # تحليل هيكل السوق
        market_structure = self.analyze_market_structure()
        signals.append(f"هيكل السوق: {market_structure}")
        
        # تحديد السيولة
        liquidity_zones = self.find_liquidity_zones()
        if liquidity_zones:
            signals.append(f"مناطق سيولة: {', '.join([f'${z:.2f}' for z in liquidity_zones])}")
        
        # تحديد الإشارة النهائية
        if market_structure == "صاعد" and volume_signal == "نشاط مؤسسي":
            signal = "شراء"
            signals.append("توافق هيكل صاعد مع دخول مؤسسي - إشارة قوية")
        elif market_structure == "هابط" and volume_signal == "نشاط مؤسسي":
            signal = "بيع"
            signals.append("توافق هيكل هابط مع خروج مؤسسي - إشارة قوية")
        else:
            signal = "محايد"
            signals.append("انتظار تأكيد واضح من السوق")
        
        return {
            "school": "SMC (Smart Money Concepts)",
            "signal": signal,
            "market_structure": market_structure,
            "confidence": self.calculate_confidence(volume_signal, market_structure),
            "details": signals
        }
    
    def find_order_blocks(self, data: pd.DataFrame) -> Dict:
        """البحث عن Order Blocks"""
        for i in range(len(data) - 2, 0, -1):
            candle = data.iloc[i]
            prev_candle = data.iloc[i-1]
            next_candle = data.iloc[i+1]
            
            # Order Block صاعد
            if (candle['close'] < candle['open'] and 
                next_candle['close'] > candle['high'] and
                candle['volume'] > data['volume'].mean()):
                return {"type": "bullish", "price": candle['high']}
            
            # Order Block هابط
            if (candle['close'] > candle['open'] and 
                next_candle['close'] < candle['low'] and
                candle['volume'] > data['volume'].mean()):
                return {"type": "bearish", "price": candle['low']}
        
        return None
    
    def analyze_market_structure(self) -> str:
        """تحليل هيكل السوق"""
        highs = self.data['high'].tail(10)
        lows = self.data['low'].tail(10)
        
        higher_highs = (highs.diff() > 0).sum()
        higher_lows = (lows.diff() > 0).sum()
        
        if higher_highs > 6 and higher_lows > 6:
            return "صاعد"
        elif higher_highs < 3 and higher_lows < 3:
            return "هابط"
        else:
            return "عرضي"
    
    def find_liquidity_zones(self) -> List[float]:
        """البحث عن مناطق السيولة"""
        recent_highs = self.data['high'].tail(50)
        recent_lows = self.data['low'].tail(50)
        
        # مناطق سيولة عند القمم والقيعان المتساوية
        liquidity = []
        
        for price in recent_highs:
            if (recent_highs == price).sum() >= 2:
                liquidity.append(price)
                break
        
        for price in recent_lows:
            if (recent_lows == price).sum() >= 2:
                liquidity.append(price)
                break
        
        return list(set(liquidity))[:3]
    
    def calculate_confidence(self, volume_signal: str, market_structure: str) -> int:
        confidence = 50
        
        if volume_signal == "نشاط مؤسسي":
            confidence += 20
        
        if market_structure != "عرضي":
            confidence += 15
        
        return min(90, confidence)
