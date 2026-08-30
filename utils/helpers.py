import pandas as pd
from typing import Dict, Any, List
from analysis.price_action import analyze_price_action
from analysis.smc import analyze_smc
from analysis.wyckoff import analyze_wyckoff
from analysis.elliott import analyze_elliott
from analysis.volume_profile import analyze_volume_profile

def run_all_analyses(df: pd.DataFrame, symbol: str) -> List[Dict[str, Any]]:
    """تشغيل كل المدارس بدوال مختلفة"""
    results = []
    results.append(analyze_price_action(df, symbol))
    results.append(analyze_smc(df, symbol))
    results.append(analyze_wyckoff(df, symbol))
    results.append(analyze_elliott(df, symbol))
    results.append(analyze_volume_profile(df, symbol))
    return results
