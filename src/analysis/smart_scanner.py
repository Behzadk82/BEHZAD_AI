# src/analysis/smart_scanner.py
# موتور جستجوی خودکار و امتیازدهی ترکیبی - نسخه نهایی

import sqlite3
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

class SmartScanner:
    def __init__(self):
        self.con = sqlite3.connect(DB_PATH, timeout=15)
        self.con.row_factory = sqlite3.Row

    def close(self):
        if self.con:
            self.con.close()

    def _get_all_codes(self):
        rows = self.con.execute("SELECT DISTINCT ins_code FROM indicators").fetchall()
        return [r["ins_code"] for r in rows]

    def _get_latest(self, ins_code):
        row = self.con.execute("""
            SELECT p.date, p.price_close, p.volume,
                   i.ma5, i.ma20, i.ma50, i.rsi14,
                   i.macd, i.macd_signal, i.macd_histogram,
                   i.bb_upper, i.bb_middle, i.bb_lower
            FROM price_history p
            JOIN indicators i ON p.ins_code = i.ins_code AND p.date = i.date
            WHERE p.ins_code = ?
            ORDER BY p.date DESC LIMIT 1
        """, (ins_code,)).fetchone()
        
        sym = self.con.execute("SELECT symbol, name FROM symbols WHERE ins_code = ?", (ins_code,)).fetchone()
        
        if not row or not sym: return None
        
        return {
            "ins_code": ins_code, "symbol": sym["symbol"], "name": sym["name"], "date": row["date"],
            "close": row["price_close"], "volume": row["volume"],
            "ma5": row["ma5"], "ma20": row["ma20"], "ma50": row["ma50"], "rsi14": row["rsi14"],
            "macd": row["macd"], "macd_signal": row["macd_signal"], "macd_hist": row["macd_histogram"],
            "bb_upper": row["bb_upper"], "bb_middle": row["bb_middle"], "bb_lower": row["bb_lower"],
        }

    def _get_volume_avg(self, ins_code, days=20):
        rows = self.con.execute("SELECT volume FROM price_history WHERE ins_code = ? ORDER BY date DESC LIMIT ?", (ins_code, days)).fetchall()
        if not rows: return 0
        return sum([r["volume"] for r in rows]) / len(rows)

    def scan(self, min_score=40, limit=50):
        """اسکن خودکار کل بازار و برگرداندن بهترین‌ها"""
        codes = self._get_all_codes()
        results = []
        
        for code in codes:
            d = self._get_latest(code)
            if not d: continue
            
            score = 0
            reasons = []
            rsi = d["rsi14"]
            
            # --- ۱. ترکیب RSI و MACD (تشخیص واگرایی و مومنتوم) ---
            if rsi is not None and d["macd"] is not None and d["macd_signal"] is not None:
                if rsi < 35 and d["macd"] > d["macd_signal"]:
                    score += 35
                    reasons.append(f"RSI={rsi:.1f} + MACD صعودی (سیگنال قوی)")
                elif rsi < 45 and d["macd"] > d["macd_signal"]:
                    score += 20
                    reasons.append(f"RSI={rsi:.1f} + MACD صعودی")
                elif rsi > 70:
                    score -= 20
                    reasons.append(f"RSI={rsi:.1f} (اشباع خرید)")

            # --- ۲. ترکیب MA و قیمت (روند) ---
            if d["ma20"] and d["ma50"]:
                if d["close"] > d["ma20"] > d["ma50"]:
                    score += 25
                    reasons.append("روند صعودی کامل (MA20 > MA50)")
                elif d["close"] > d["ma50"]:
                    score += 10
                    reasons.append("بالای MA50")

            # --- ۳. ترکیب بولینگر و حجم (انفجار قیمتی) ---
            vol_avg = self._get_volume_avg(code)
            if vol_avg > 0 and d["bb_upper"] and d["bb_lower"]:
                bb_width = (d["bb_upper"] - d["bb_lower"]) / d["bb_middle"] if d["bb_middle"] else 0
                if bb_width < 0.15 and d["volume"] > vol_avg * 1.5:
                    score += 20
                    reasons.append("فشردگی بولینگر + حجم بالا (آماده انفجار)")
                elif d["close"] <= d["bb_lower"] * 1.02:
                    score += 10
                    reasons.append("نزدیک کف بولینگر")

            # محدود کردن امتیاز
            score = max(0, min(100, score))
            
            if score >= min_score:
                results.append({
                    "ins_code": code, "symbol": d["symbol"], "name": d["name"], "close": d["close"],
                    "score": score, "reasons": reasons, "rsi": round(rsi, 1) if rsi else None,
                    "volume_ratio": round(d["volume"] / vol_avg, 2) if vol_avg else None,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

if __name__ == "__main__":
    print("=" * 70)
    print("SMART SCANNER - موتور جستجوی خودکار")
    print("=" * 70)
    scanner = SmartScanner()
    results = scanner.scan(min_score=40, limit=30)
    scanner.close()
    
    print(f"تعداد {len(results)} نماد مستعد پیدا شد:\n")
    print(f"{'#':>3} | {'نماد':12s} | {'امتیاز':>5s} | {'RSI':>6s} | دلایل")
    print("-" * 90)
    for i, r in enumerate(results, 1):
        reasons = ", ".join(r["reasons"][:2])
        print(f"{i:>3} | {r['symbol'][:12]:12s} | {r['score']:>5d} | {str(r['rsi']):>6s} | {reasons}")
