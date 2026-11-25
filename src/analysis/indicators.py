# src/analysis/indicators.py
# Technical indicators calculation - Phase 2.1
# All calculations are pure Python (no pandas/numpy needed).

import sqlite3
from typing import List, Dict, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH


class Indicators:
    """Calculate technical indicators from price_history data."""

    def __init__(self, ins_code: str):
        self.ins_code = ins_code
        self.prices = []  # list of dicts with 'date', 'close', 'volume'

    # ---------- Data loading ----------
    def load_from_db(self):
        """Load price history from SQLite, sorted by date."""
        con = sqlite3.connect(DB_PATH, timeout=15)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT date, price_close, volume FROM price_history "
            "WHERE ins_code = ? ORDER BY date ASC",
            (self.ins_code,)
        ).fetchall()
        con.close()
        
        self.prices = [
            {"date": r["date"], "close": r["price_close"], "volume": r["volume"]}
            for r in rows
        ]
        return len(self.prices)

    # ---------- MA ----------
    def sma(self, period: int) -> List[Optional[float]]:
        """Simple Moving Average."""
        result = [None] * len(self.prices)
        closes = [p["close"] for p in self.prices]
        
        for i in range(period - 1, len(closes)):
            window = closes[i - period + 1:i + 1]
            result[i] = sum(window) / period
        return result

    # ---------- EMA ----------
    def ema(self, period: int) -> List[Optional[float]]:
        """Exponential Moving Average."""
        result = [None] * len(self.prices)
        closes = [p["close"] for p in self.prices]
        
        if len(closes) < period:
            return result
        
        multiplier = 2 / (period + 1)
        result[period - 1] = sum(closes[:period]) / period
        
        for i in range(period, len(closes)):
            result[i] = (closes[i] - result[i-1]) * multiplier + result[i-1]
        return result

    # ---------- RSI ----------
    def rsi(self, period: int = 14) -> List[Optional[float]]:
        """Relative Strength Index."""
        result = [None] * len(self.prices)
        closes = [p["close"] for p in self.prices]
        
        if len(closes) < period + 1:
            return result
        
        # Calculate gains and losses
        gains = []
        losses = []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-change)
        
        # First average
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            result[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[period] = 100 - (100 / (1 + rs))
        
        # Smoothed averages
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                result[i + 1] = 100.0
            else:
                rs = avg_gain / avg_loss
                result[i + 1] = 100 - (100 / (1 + rs))
        
        return result

    # ---------- MACD ----------
    def macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[Optional[float]]]:
        """MACD line, signal line, and histogram."""
        ema_fast = self.ema(fast)
        ema_slow = self.ema(slow)
        
        macd_line = [None] * len(self.prices)
        for i in range(len(self.prices)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd_line[i] = ema_fast[i] - ema_slow[i]
        
        # Signal line (EMA of MACD)
        signal_line = [None] * len(self.prices)
        valid_macd = [(i, v) for i, v in enumerate(macd_line) if v is not None]
        
        if len(valid_macd) >= signal:
            multiplier = 2 / (signal + 1)
            start_idx = valid_macd[signal - 1][0]
            start_val = sum(v for _, v in valid_macd[:signal]) / signal
            signal_line[start_idx] = start_val
            
            for i in range(signal, len(valid_macd)):
                idx = valid_macd[i][0]
                prev = signal_line[valid_macd[i-1][0]]
                signal_line[idx] = (valid_macd[i][1] - prev) * multiplier + prev
        
        histogram = [None] * len(self.prices)
        for i in range(len(self.prices)):
            if macd_line[i] is not None and signal_line[i] is not None:
                histogram[i] = macd_line[i] - signal_line[i]
        
        return {"macd": macd_line, "signal": signal_line, "histogram": histogram}

    # ---------- Bollinger Bands ----------
    def bollinger(self, period: int = 20, num_std: float = 2.0) -> Dict[str, List[Optional[float]]]:
        """Bollinger Bands (upper, middle, lower)."""
        middle = self.sma(period)
        upper = [None] * len(self.prices)
        lower = [None] * len(self.prices)
        closes = [p["close"] for p in self.prices]
        
        for i in range(period - 1, len(closes)):
            window = closes[i - period + 1:i + 1]
            mean = middle[i]
            if mean is None:
                continue
            variance = sum((x - mean) ** 2 for x in window) / period
            std = variance ** 0.5
            upper[i] = mean + num_std * std
            lower[i] = mean - num_std * std
        
        return {"upper": upper, "middle": middle, "lower": lower}

    # ---------- Summary ----------
    def summary(self) -> Dict:
        """Last value of each indicator."""
        if not self.prices:
            return {}
        
        ma5 = self.sma(5)
        ma20 = self.sma(20)
        rsi14 = self.rsi(14)
        macd_data = self.macd()
        bb = self.bollinger()
        
        last = len(self.prices) - 1
        return {
            "date": self.prices[last]["date"],
            "close": self.prices[last]["close"],
            "ma5": ma5[last],
            "ma20": ma20[last],
            "rsi14": rsi14[last],
            "macd": macd_data["macd"][last],
            "macd_signal": macd_data["signal"][last],
            "macd_histogram": macd_data["histogram"][last],
            "bb_upper": bb["upper"][last],
            "bb_middle": bb["middle"][last],
            "bb_lower": bb["lower"][last],
        }


if __name__ == "__main__":
    ins_code = "46348559193224090"  # FOLAD
    
    print("=" * 60)
    print("INDICATORS TEST - FOLAD")
    print("=" * 60)
    
    ind = Indicators(ins_code)
    count = ind.load_from_db()
    print(f"Loaded {count} records from DB")
    
    if count == 0:
        print("[ERROR] No data. Run history.py + migrate_history.py first.")
        raise SystemExit(1)
    
    print(f"Date range: {ind.prices[0]['date']} -> {ind.prices[-1]['date']}")
    print()
    
    summary = ind.summary()
    print("Latest indicator values:")
    print("-" * 60)
    for k, v in summary.items():
        if v is None:
            print(f"  {k:20s} = None (insufficient data)")
        elif isinstance(v, float):
            print(f"  {k:20s} = {v:.2f}")
        else:
            print(f"  {k:20s} = {v}")
    
    print()
    print("Last 5 days of MA5 and MA20:")
    print("-" * 60)
    ma5 = ind.sma(5)
    ma20 = ind.sma(20)
    for i in range(max(0, count - 5), count):
        p = ind.prices[i]
        ma5_v = f"{ma5[i]:.1f}" if ma5[i] is not None else "N/A"
        ma20_v = f"{ma20[i]:.1f}" if ma20[i] is not None else "N/A"
        print(f"  {p['date']} | close={p['close']:.1f} | MA5={ma5_v} | MA20={ma20_v}")
    
    print()
    print("=" * 60)
    print("INDICATORS TEST COMPLETE")
    print("=" * 60)
