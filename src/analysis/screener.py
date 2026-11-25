# src/analysis/screener.py
# Screening engine - Phase 3
# Finds symbols matching predefined strategies.

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH


class Screener:
    def __init__(self):
        self.con = sqlite3.connect(DB_PATH, timeout=15)
        self.con.row_factory = sqlite3.Row

    def close(self):
        if self.con:
            self.con.close()

    def _get_symbols_with_history(self):
        """Return ins_codes that have at least one row in price_history."""
        rows = self.con.execute(
            "SELECT DISTINCT ins_code FROM price_history"
        ).fetchall()
        return [r["ins_code"] for r in rows]

    def _get_latest_data(self, ins_code):
        """Get latest price and indicators for one symbol."""
        price = self.con.execute(
            "SELECT * FROM price_history WHERE ins_code = ? ORDER BY date DESC LIMIT 1",
            (ins_code,)
        ).fetchone()
        
        ind = self.con.execute(
            "SELECT * FROM indicators WHERE ins_code = ? ORDER BY date DESC LIMIT 1",
            (ins_code,)
        ).fetchone()
        
        sym = self.con.execute(
            "SELECT symbol, name FROM symbols WHERE ins_code = ?",
            (ins_code,)
        ).fetchone()
        
        if not price or not ind or not sym:
            return None
        
        return {
            "ins_code": ins_code,
            "symbol": sym["symbol"],
            "name": sym["name"],
            "date": price["date"],
            "close": price["price_close"],
            "volume": price["volume"],
            "trades": price["trades"],
            "ma5": ind["ma5"],
            "ma20": ind["ma20"],
            "ma50": ind["ma50"],
            "rsi14": ind["rsi14"],
            "macd": ind["macd"],
            "macd_signal": ind["macd_signal"],
            "macd_hist": ind["macd_histogram"],
            "bb_upper": ind["bb_upper"],
            "bb_lower": ind["bb_lower"],
        }

    def _get_previous_macd(self, ins_code):
        """Get MACD from 2 days ago to detect cross."""
        rows = self.con.execute(
            "SELECT macd, macd_signal FROM indicators "
            "WHERE ins_code = ? ORDER BY date DESC LIMIT 2",
            (ins_code,)
        ).fetchall()
        if len(rows) < 2:
            return None
        return {"current": dict(rows[0]), "previous": dict(rows[1])}

    # ---------- Strategies ----------
    def screen_oversold(self):
        """RSI < 30 (oversold - potential buy)."""
        results = []
        for code in self._get_symbols_with_history():
            d = self._get_latest_data(code)
            if d and d["rsi14"] is not None and d["rsi14"] < 30:
                results.append({**d, "signal": "OVERSOLD", "reason": f"RSI={d['rsi14']:.1f}"})
        return results

    def screen_overbought(self):
        """RSI > 70 (overbought - potential sell)."""
        results = []
        for code in self._get_symbols_with_history():
            d = self._get_latest_data(code)
            if d and d["rsi14"] is not None and d["rsi14"] > 70:
                results.append({**d, "signal": "OVERBOUGHT", "reason": f"RSI={d['rsi14']:.1f}"})
        return results

    def screen_macd_bullish_cross(self):
        """MACD crossed above Signal (golden cross)."""
        results = []
        for code in self._get_symbols_with_history():
            d = self._get_latest_data(code)
            if not d:
                continue
            prev = self._get_previous_macd(code)
            if not prev:
                continue
            cur = prev["current"]
            old = prev["previous"]
            if (cur["macd"] is not None and cur["macd_signal"] is not None and
                old["macd"] is not None and old["macd_signal"] is not None):
                if old["macd"] <= old["macd_signal"] and cur["macd"] > cur["macd_signal"]:
                    results.append({**d, "signal": "MACD_GOLDEN_CROSS",
                                    "reason": f"MACD({cur['macd']:.1f}) > Signal({cur['macd_signal']:.1f})"})
        return results

    def screen_ma_bullish(self):
        """MA5 > MA20 > MA50 (uptrend confirmed)."""
        results = []
        for code in self._get_symbols_with_history():
            d = self._get_latest_data(code)
            if (d and d["ma5"] is not None and d["ma20"] is not None and d["ma50"] is not None and
                d["ma5"] > d["ma20"] > d["ma50"]):
                results.append({**d, "signal": "MA_BULLISH",
                                "reason": f"MA5({d['ma5']:.0f}) > MA20({d['ma20']:.0f}) > MA50({d['ma50']:.0f})"})
        return results

    def screen_near_support(self):
        """Price near lower Bollinger band (potential bounce)."""
        results = []
        for code in self._get_symbols_with_history():
            d = self._get_latest_data(code)
            if not d or d["bb_lower"] is None or d["bb_upper"] is None:
                continue
            if d["close"] <= d["bb_lower"] * 1.02:  # within 2% of lower band
                pct = (d["close"] - d["bb_lower"]) / d["bb_lower"] * 100
                results.append({**d, "signal": "NEAR_SUPPORT",
                                "reason": f"{pct:+.1f}% from BB lower"})
        return results

    def screen_near_resistance(self):
        """Price near upper Bollinger band (potential resistance)."""
        results = []
        for code in self._get_symbols_with_history():
            d = self._get_latest_data(code)
            if not d or d["bb_lower"] is None or d["bb_upper"] is None:
                continue
            if d["close"] >= d["bb_upper"] * 0.98:
                pct = (d["close"] - d["bb_upper"]) / d["bb_upper"] * 100
                results.append({**d, "signal": "NEAR_RESISTANCE",
                                "reason": f"{pct:+.1f}% from BB upper"})
        return results

    def screen_high_volume(self, threshold_ratio=2.0):
        """Today's volume > 2x average volume of last 20 days."""
        results = []
        for code in self._get_symbols_with_history():
            rows = self.con.execute(
                "SELECT volume FROM price_history WHERE ins_code = ? ORDER BY date DESC LIMIT 20",
                (code,)
            ).fetchall()
            if len(rows) < 20:
                continue
            volumes = [r["volume"] for r in rows]
            avg = sum(volumes[1:]) / 19  # exclude today
            today = volumes[0]
            if avg > 0 and today > avg * threshold_ratio:
                d = self._get_latest_data(code)
                if d:
                    results.append({**d, "signal": "HIGH_VOLUME",
                                    "reason": f"Today {today/avg:.1f}x avg"})
        return results

    # ---------- All strategies ----------
    def run_all(self):
        return {
            "OVERSOLD": self.screen_oversold(),
            "OVERBOUGHT": self.screen_overbought(),
            "MACD_GOLDEN_CROSS": self.screen_macd_bullish_cross(),
            "MA_BULLISH": self.screen_ma_bullish(),
            "NEAR_SUPPORT": self.screen_near_support(),
            "NEAR_RESISTANCE": self.screen_near_resistance(),
            "HIGH_VOLUME": self.screen_high_volume(),
        }


if __name__ == "__main__":
    print("=" * 70)
    print("SCREENER - FINDING OPPORTUNITIES")
    print("=" * 70)
    print()

    sc = Screener()
    results = sc.run_all()

    for signal, items in results.items():
        print(f"--- {signal} ({len(items)} found) ---")
        for item in items[:10]:  # show first 10 per strategy
            print(f"  {item['symbol']:10s} | {item['name'][:30]:30s} | {item['reason']}")
        if len(items) > 10:
            print(f"  ... and {len(items) - 10} more")
        print()

    sc.close()
    print("=" * 70)
    print("SCREENING COMPLETE")
    print("=" * 70)
