# src/analysis/deep_analyzer.py
# موتور تحلیل چندلایه (Deep Multi-Layer Analysis)
# این فایل جایگزین کامل smart_scanner می‌شود و با ۵ لایه تحلیل می‌کند.

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

class DeepAnalyzer:
    def __init__(self):
        self.con = sqlite3.connect(DB_PATH, timeout=15)
        self.con.row_factory = sqlite3.Row

    def close(self):
        if self.con: self.con.close()

    def _get_all_codes(self):
        return [r["ins_code"] for r in self.con.execute("SELECT DISTINCT ins_code FROM indicators").fetchall()]

    def _get_history(self, ins_code, limit=260):
        rows = self.con.execute("""
            SELECT p.date, p.price_close, p.volume,
                   i.ma5, i.ma20, i.ma50, i.rsi14,
                   i.macd, i.macd_signal, i.bb_upper, i.bb_lower
            FROM price_history p
            JOIN indicators i ON p.ins_code = i.ins_code AND p.date = i.date
            WHERE p.ins_code = ?
            ORDER BY p.date DESC LIMIT ?
        """, (ins_code, limit)).fetchall()
        
        sym = self.con.execute("SELECT symbol, name FROM symbols WHERE ins_code = ?", (ins_code,)).fetchone()
        if not rows or not sym: return None
        
        return {
            "symbol": sym["symbol"], 
            "name": sym["name"],
            "rows": [dict(r) for r in reversed(rows)]
        }

    def analyze(self, ins_code):
        data = self._get_history(ins_code)
        if not data or len(data["rows"]) < 50: return None
        
        rows = data["rows"]
        last = rows[-1]
        prev = rows[-2]
        
        score = 0
        reasons = []
        warnings = []

        # =========================================================
        # لایه ۱: تحلیل تکنیکال (Technical Analysis)
        # =========================================================
        # RSI
        if last["rsi14"]:
            if last["rsi14"] < 35:
                score += 25
                reasons.append(f"RSI({last['rsi14']:.0f}) oversold")
            elif last["rsi14"] > 70:
                score -= 20
                warnings.append(f"RSI({last['rsi14']:.0f}) overbought")
        
        # MACD
        if last["macd"] and last["macd_signal"]:
            if last["macd"] > last["macd_signal"]:
                score += 20
                reasons.append("MACD صعودی")
            else:
                score -= 10
                warnings.append("MACD نزولی")

        # =========================================================
        # لایه ۲: تحلیل روند (Trend)
        # =========================================================
        if last["ma20"] and last["ma50"]:
            if last["price_close"] > last["ma20"] > last["ma50"]:
                score += 20
                reasons.append("روند کامل (MA20 > MA50)")
            elif last["price_close"] < last["ma50"]:
                score -= 15
                warnings.append("زیر MA50 (روند نزولی)")

        # =========================================================
        # لایه ۳: تحلیل حجم (Volume Analysis)
        # =========================================================
        avg_vol = sum(r["volume"] for r in rows[-20:-1]) / 19
        if avg_vol > 0:
            if last["volume"] > avg_vol * 1.5:
                score += 20
                reasons.append(f"حجم {last['volume']/avg_vol:.1f}x")
            elif last["volume"] < avg_vol * 0.5:
                score -= 15
                warnings.append("حجم بسیار کم (بی‌تحرک)")

        # =========================================================
        # لایه ۴: تحلیل حمایت/مقاومت (Support/Resistance)
        # =========================================================
        high_52w = max(r["price_close"] for r in rows)
        low_52w = min(r["price_close"] for r in rows)
        price_pos = (last["price_close"] - low_52w) / (high_52w - low_52w) * 100 if high_52w > low_52w else 50
        
        if price_pos > 90:
            score -= 25
            warnings.append(f"نزدیک سقف 52 هفته (ریسک اصلاح)")
        elif price_pos < 20:
            score += 15
            reasons.append(f"نزدیک کف 52 هفته (فرصت)")

        # =========================================================
        # لایه ۵: فیلترهای محافظ نهایی (Safety Filters)
        # =========================================================
        # رشد بیش از حد در ۲۰ روز
        price_20d_ago = rows[-20]["price_close"]
        if price_20d_ago > 0:
            growth_20d = (last["price_close"] - price_20d_ago) / price_20d_ago * 100
            if growth_20d > 30:
                score -= 30
                warnings.append(f"رشد {growth_20d:.0f}% در ۲۰ روز (حباب)")

        score = max(0, min(100, score))
        
        return {
            "ins_code": ins_code,
            "symbol": data["symbol"],
            "name": data["name"],
            "close": last["price_close"],
            "score": score,
            "reasons": reasons,
            "warnings": warnings,
            "rsi": round(last["rsi14"], 1) if last["rsi14"] else None,
        }

    def scan_all(self, min_score=40):
        codes = self._get_all_codes()
        results = []
        
        for code in codes:
            analysis = self.analyze(code)
            if analysis and analysis["score"] >= min_score:
                results.append(analysis)
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results
