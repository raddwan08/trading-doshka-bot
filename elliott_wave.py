import pandas as pd
import numpy as np
from typing import Dict, List

class ElliottWaveAnalyzer:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.signals = []
    
    def analyze(self) -> Dict:
        """تحليل موجات إليوت"""
        signals = []
        
        # تحديد الموجات
        waves = self.identify_waves()
        current_wave = self.identify_current_wave(waves)
        
        signals.append(f"الموجة الحالية: {current_wave}")
        
        # تحديد موقعنا في الموجة
        wave_position = self.calculate_wave_position()
        signals.append(f"موقع السعر في الموجة: {wave_position}%")
        
        # توقع الموجة التالية
        next_wave = self.predict_next_wave(current_wave)
        signals.append(f"الموجة المتوقعة التالية: {next_wave}")
        
        # تحديد الإشارة
        if current_wave in ["Wave 1", "Wave 3", "Wave 5"]:
            signal = "شراء"
            signals.append("موجة صاعدة - اتجاه شرائي")
        elif current_wave in ["Wave 2", "Wave 4", "Wave A", "Wave C"]:
            signal = "بيع"
            signals.append("موجة هابطة - اتجاه بيعي")
        else:
            signal = "محايد"
        
        # حساب أهداف الموجة
        targets = self.calculate_wave_targets(current_wave)
        if targets:
            signals.append(f"أهداف السعر: {targets}")
        
        return {
            "school": "Elliott Wave",
            "current_wave": current_wave,
            "next_wave": next_wave,
            "signal": signal,
            "confidence": self.calculate_confidence(current_wave),
            "details": signals
        }
    
    def identify_waves(self) -> List[Dict]:
        """تحديد الموجات من البيانات"""
        waves = []
        price_data = self.data['close'].values
        
        # تحديد القمم والقيعان
        peaks = []
        troughs = []
        
        for i in range(2, len(price_data) - 2):
            if (price_data[i] > price_data[i-1] and 
                price_data[i] > price_data[i-2] and
                price_data[i] > price_data[i+1] and 
                price_data[i] > price_data[i+2]):
                peaks.append({"index": i, "price": price_data[i]})
            
            if (price_data[i] < price_data[i-1] and 
                price_data[i] < price_data[i-2] and
                price_data[i] < price_data[i+1] and 
                price_data[i] < price_data[i+2]):
                troughs.append({"index": i, "price": price_data[i]})
        
        # بناء الموجات
        all_turns = sorted(peaks + troughs, key=lambda x: x["index"])
        
        for i in range(len(all_turns) - 1):
            wave = {
                "start_index": all_turns[i]["index"],
                "end_index": all_turns[i+1]["index"],
                "start_price": all_turns[i]["price"],
                "end_price": all_turns[i+1]["price"],
                "type": "up" if all_turns[i+1]["price"] > all_turns[i]["price"] else "down"
            }
            waves.append(wave)
        
        return waves[-8:]  # آخر 8 موجات
    
    def identify_current_wave(self, waves: List[Dict]) -> str:
        """تحديد الموجة الحالية"""
        if len(waves) < 3:
            return "Wave 1"
        
        # عد الموجات الصاعدة والهابطة
        up_waves = [w for w in waves if w["type"] == "up"]
        down_waves = [w for w in waves if w["type"] == "down"]
        
        if len(up_waves) > len(down_waves):
            return f"Wave {len(up_waves)}"
        else:
            return f"Wave {len(up_waves)}" if waves[-1]["type"] == "up" else f"Corrective Wave"
    
    def calculate_wave_position(self) -> float:
        """حساب موقع السعر ضمن الموجة"""
        recent_data = self.data.tail(10)
        wave_high = recent_data['high'].max()
        wave_low = recent_data['low'].min()
        current_price = recent_data['close'].iloc[-1]
        
        if wave_high == wave_low:
            return 50.0
        
        position = ((current_price - wave_low) / (wave_high - wave_low)) * 100
        return round(position, 2)
    
    def predict_next_wave(self, current_wave: str) -> str:
        """توقع الموجة التالية"""
        wave_map = {
            "Wave 1": "Wave 2 (تصحيحية)",
            "Wave 2": "Wave 3 (الأقوى)",
            "Wave 3": "Wave 4 (تصحيحية)",
            "Wave 4": "Wave 5 (نهائية)",
            "Wave 5": "Wave A (تصحيح)",
            "Corrective Wave": "موجة دافعة جديدة"
        }
        return wave_map.get(current_wave, "غير محدد")
    
    def calculate_wave_targets(self, current_wave: str) -> str:
        """حساب أهداف الموجة"""
        recent_price = self.data['close'].iloc[-1]
        
        if current_wave in ["Wave 1", "Wave 3", "Wave 5"]:
            target1 = recent_price * 1.05
            target2 = recent_price * 1.10
            return f"T1: ${target1:.2f}, T2: ${target2:.2f}"
        elif current_wave in ["Wave 2", "Wave 4"]:
            target1 = recent_price * 0.95
            target2 = recent_price * 0.90
            return f"T1: ${target1:.2f}, T2: ${target2:.2f}"
        else:
            return ""
    
    def calculate_confidence(self, current_wave: str) -> int:
        if current_wave == "Wave 3":
            return 80
        elif current_wave in ["Wave 1", "Wave 5"]:
            return 70
        elif current_wave in ["Wave 2", "Wave 4"]:
            return 60
        else:
            return 50
