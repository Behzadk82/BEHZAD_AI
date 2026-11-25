# src/analysis/advanced_indicators.py
# اندیکاتورهای پیشرفته: ATR, ADX, OBV, Stochastic, Ichimoku, Fibonacci

import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

class AdvancedIndicators:
    def __init__(self, ins_code: str):
        self.ins_code = ins_code
        self.prices = []  # dict with date, close, high, low, volume

    def load_from_db(self):
        con = sqlite3.connect(DB_PATH, timeout=15)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT date, price_close, price_max, price_min, volume "
            "FROM price_history WHERE ins_code = ? ORDER BY date ASC",
            (self.ins_code,)
        ).fetchall()
        con.close()
        self.prices = [dict(r) for r in rows]
        return len(self.prices)

    # ═══════════════════════════════════════════════════════
    # 1. ATR (Average True Range)
    # ═══════════════════════════════════════════════════════
    def atr(self, period: int = 14) -> List[Optional[float]]:
        n = len(self.prices)
        if n < period + 1: return [None] * n
        
        tr_list = [None]
        for i in range(1, n):
            h = self.prices[i]["price_max"]
            l = self.prices[i]["price_min"]
            pc = self.prices[i-1]["price_close"]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            tr_list.append(tr)
        
        atr_list = [None] * n
        atr_list[period] = sum(tr_list[1:period+1]) / period
        for i in range(period + 1, n):
            atr_list[i] = (atr_list[i-1] * (period - 1) + tr_list[i]) / period
        
        return atr_list

    # ═══════════════════════════════════════════════════════
    # 2. ADX (Average Directional Index)
    # ═══════════════════════════════════════════════════════
    def adx(self, period: int = 14) -> Dict[str, List[Optional[float]]]:
        n = len(self.prices)
        if n < period * 2: return {"adx": [None]*n, "plus_di": [None]*n, "minus_di": [None]*n}
        
        tr_list = [0] * n
        plus_dm = [0] * n
        minus_dm = [0] * n
        
        for i in range(1, n):
            h = self.prices[i]["price_max"]
            l = self.prices[i]["price_min"]
            ph = self.prices[i-1]["price_max"]
            pl = self.prices[i-1]["price_min"]
            pc = self.prices[i-1]["price_close"]
            tr_list[i] = max(h - l, abs(h - pc), abs(l - pc))
            up = h - ph
            down = pl - l
            plus_dm[i] = up if (up > down and up > 0) else 0
            minus_dm[i] = down if (down > up and down > 0) else 0
        
        def smooth(arr, p):
            out = [None] * n
            out[p] = sum(arr[1:p+1])
            for i in range(p + 1, n):
                out[i] = out[i-1] - (out[i-1] / p) + arr[i]
            return out
        
        tr_s = smooth(tr_list, period)
        plus_s = smooth(plus_dm, period)
        minus_s = smooth(minus_dm, period)
        
        plus_di = [None] * n
        minus_di = [None] * n
        for i in range(period, n):
            if tr_s[i] and tr_s[i] > 0:
                plus_di[i] = 100 * plus_s[i] / tr_s[i]
                minus_di[i] = 100 * minus_s[i] / tr_s[i]
        
        dx = [None] * n
        for i in range(period, n):
            if plus_di[i] is not None and minus_di[i] is not None:
                s = plus_di[i] + minus_di[i]
                if s > 0:
                    dx[i] = 100 * abs(plus_di[i] - minus_di[i]) / s
        
        adx_list = [None] * n
        first_valid = None
        for i in range(period, n):
            if dx[i] is not None:
                if first_valid is None:
                    window = [dx[j] for j in range(i - period + 1, i + 1) if dx[j] is not None]
                    if len(window) == period:
                        adx_list[i] = sum(window) / period
                        first_valid = i
                else:
                    if adx_list[i-1] is not None:
                        adx_list[i] = (adx_list[i-1] * (period - 1) + dx[i]) / period
        
        return {"adx": adx_list, "plus_di": plus_di, "minus_di": minus_di}

    # ═══════════════════════════════════════════════════════
    # 3. OBV (On-Balance Volume)
    # ═══════════════════════════════════════════════════════
    def obv(self) -> List[float]:
        n = len(self.prices)
        result = [0.0] * n
        for i in range(1, n):
            if self.prices[i]["price_close"] > self.prices[i-1]["price_close"]:
                result[i] = result[i-1] + self.prices[i]["volume"]
            elif self.prices[i]["price_close"] < self.prices[i-1]["price_close"]:
                result[i] = result[i-1] - self.prices[i]["volume"]
            else:
                result[i] = result[i-1]
        return result

    # ═══════════════════════════════════════════════════════
    # 4. Stochastic Oscillator
    # ═══════════════════════════════════════════════════════
    def stochastic(self, k_period: int = 14, d_period: int = 3) -> Dict[str, List[Optional[float]]]:
        n = len(self.prices)
        k_line = [None] * n
        d_line = [None] * n
        
        for i in range(k_period - 1, n):
            window = self.prices[i - k_period + 1:i + 1]
            high = max(r["price_max"] for r in window)
            low = min(r["price_min"] for r in window)
            if high - low > 0:
                k_line[i] = 100 * (self.prices[i]["price_close"] - low) / (high - low)
        
        for i in range(k_period + d_period - 2, n):
            window = [k_line[j] for j in range(i - d_period + 1, i + 1) if k_line[j] is not None]
            if len(window) == d_period:
                d_line[i] = sum(window) / d_period
        
        return {"k": k_line, "d": d_line}

    # ═══════════════════════════════════════════════════════
    # 5. Ichimoku Cloud
    # ═══════════════════════════════════════════════════════
    def ichimoku(self) -> Dict[str, List[Optional[float]]]:
        n = len(self.prices)
        tenkan = [None] * n
        kijun = [None] * n
        senkou_a = [None] * n
        senkou_b = [None] * n
        chikou = [None] * n
        
        def high_low(start, end):
            window = self.prices[start:end+1]
            if not window: return None, None
            return max(r["price_max"] for r in window), min(r["price_min"] for r in window)
        
        for i in range(8, n):  # Tenkan (9)
            h, l = high_low(i-8, i)
            if h is not None: tenkan[i] = (h + l) / 2
        
        for i in range(25, n):  # Kijun (26)
            h, l = high_low(i-25, i)
            if h is not None: kijun[i] = (h + l) / 2
        
        for i in range(25, n):  # Senkou A
            if tenkan[i] is not None and kijun[i] is not None:
                senkou_a[i] = (tenkan[i] + kijun[i]) / 2
        
        for i in range(51, n):  # Senkou B (52)
            h, l = high_low(i-51, i)
            if h is not None: senkou_b[i] = (h + l) / 2
        
        for i in range(0, n - 25):  # Chikou (lagging)
            chikou[i] = self.prices[i+25]["price_close"]
        
        return {"tenkan": tenkan, "kijun": kijun, "senkou_a": senkou_a,
                "senkou_b": senkou_b, "chikou": chikou}

    # ═══════════════════════════════════════════════════════
    # 6. Fibonacci Retracement (نقاط کلیدی)
    # ═══════════════════════════════════════════════════════
    def fibonacci_levels(self, lookback: int = 100) -> Dict[str, float]:
        if len(self.prices) < lookback: lookback = len(self.prices)
        recent = self.prices[-lookback:]
        high = max(r["price_max"] for r in recent)
        low = min(r["price_min"] for r in recent)
        diff = high - low
        return {
            "high": high,
            "low": low,
            "level_0": low,
            "level_236": low + 0.236 * diff,
            "level_382": low + 0.382 * diff,
            "level_500": low + 0.5 * diff,
            "level_618": low + 0.618 * diff,
            "level_786": low + 0.786 * diff,
            "level_1000": high,
        }


# ─── تست ───
if __name__ == "__main__":
    ins_code = "46348559193224090"
    ind = AdvancedIndicators(ins_code)
    count = ind.load_from_db()
    print(f"Loaded {count} records")
    
    if count == 0:
        raise SystemExit(1)
    
    print("\n--- ATR (14) ---")
    atr = ind.atr(14)
    print(f"  Last ATR: {atr[-1]:.2f}" if atr[-1] else "  insufficient data")
    
    print("\n--- ADX (14) ---")
    adx = ind.adx(14)
    if adx["adx"][-1]:
        print(f"  ADX: {adx['adx'][-1]:.2f}")
        print(f"  +DI: {adx['plus_di'][-1]:.2f}")
        print(f"  -DI: {adx['minus_di'][-1]:.2f}")
        trend = "صعودی" if adx['plus_di'][-1] > adx['minus_di'][-1] else "نزولی"
        strength = "قوی" if adx['adx'][-1] > 25 else "ضعیف"
        print(f"  روند: {trend} ({strength})")
    
    print("\n--- OBV ---")
    obv = ind.obv()
    print(f"  Last OBV: {obv[-1]:,.0f}")
    
    print("\n--- Stochastic (14,3) ---")
    st = ind.stochastic()
    if st["k"][-1]:
        print(f"  %K: {st['k'][-1]:.2f}")
        print(f"  %D: {st['d'][-1]:.2f}" if st["d"][-1] else "  %D: insufficient")
    
    print("\n--- Ichimoku ---")
    ich = ind.ichimoku()
    print(f"  Tenkan:  {ich['tenkan'][-1]:.2f}" if ich["tenkan"][-1] else "  Tenkan: N/A")
    print(f"  Kijun:   {ich['kijun'][-1]:.2f}" if ich["kijun"][-1] else "  Kijun: N/A")
    print(f"  Senkou A: {ich['senkou_a'][-1]:.2f}" if ich["senkou_a"][-1] else "  Senkou A: N/A")
    print(f"  Senkou B: {ich['senkou_b'][-1]:.2f}" if ich["senkou_b"][-1] else "  Senkou B: N/A")
    
    print("\n--- Fibonacci (100 روز اخیر) ---")
    fib = ind.fibonacci_levels(100)
    print(f"  High:     {fib['high']:,.0f}")
    print(f"  Low:      {fib['low']:,.0f}")
    print(f"  23.6%:    {fib['level_236']:,.0f}")
    print(f"  38.2%:    {fib['level_382']:,.0f}")
    print(f"  50.0%:    {fib['level_500']:,.0f}")
    print(f"  61.8%:    {fib['level_618']:,.0f}")
    print(f"  78.6%:    {fib['level_786']:,.0f}")
