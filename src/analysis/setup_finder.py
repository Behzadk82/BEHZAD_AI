# src/analysis/setup_finder.py
# Multi-indicator confluence scoring - Phase 4.2 (fixed RSI logic)

import sqlite3
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH


class SetupFinder:
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
        
        sym = self.con.execute(
            "SELECT symbol, name FROM symbols WHERE ins_code = ?",
            (ins_code,)
        ).fetchone()
        
        if not row or not sym:
            return None
        
        return {
            "ins_code": ins_code,
            "symbol": sym["symbol"],
            "name": sym["name"],
            "date": row["date"],
            "close": row["price_close"],
            "volume": row["volume"],
            "ma5": row["ma5"], "ma20": row["ma20"], "ma50": row["ma50"],
            "rsi14": row["rsi14"],
            "macd": row["macd"], "macd_signal": row["macd_signal"],
            "macd_hist": row["macd_histogram"],
            "bb_upper": row["bb_upper"], "bb_middle": row["bb_middle"], "bb_lower": row["bb_lower"],
        }

    def _get_volume_avg(self, ins_code, days=20):
        rows = self.con.execute(
            "SELECT volume FROM price_history WHERE ins_code = ? "
            "ORDER BY date DESC LIMIT ?",
            (ins_code, days)
        ).fetchall()
        if not rows:
            return 0
        vols = [r["volume"] for r in rows]
        return sum(vols) / len(vols)

    def score_symbol(self, ins_code):
        d = self._get_latest(ins_code)
        if not d:
            return None
        
        score = 0
        reasons = []
        
        # --- 1. RSI Zones (اصلاح‌شده) ---
        rsi = d["rsi14"]
        if rsi is not None:
            if rsi < 30:
                score += 25
                reasons.append(f"RSI={rsi:.1f} (oversold)")
            elif rsi < 40:
                score += 15
                reasons.append(f"RSI={rsi:.1f} (near oversold)")
            elif rsi < 50:
                score += 5
            elif rsi < 60:
                score += 0
            elif rsi < 70:
                score -= 10
                reasons.append(f"RSI={rsi:.1f} (getting hot)")
            elif rsi < 80:
                score -= 20
                reasons.append(f"RSI={rsi:.1f} (overbought)")
            else:
                score -= 30
                reasons.append(f"RSI={rsi:.1f} (extreme overbought)")
        
        # --- 2. MACD ---
        if d["macd"] is not None and d["macd_signal"] is not None:
            if d["macd"] > d["macd_signal"]:
                score += 20
                reasons.append("MACD > Signal")
            if d["macd_hist"] is not None and d["macd_hist"] > 0:
                score += 5
        
        # --- 3. Price > MA50 ---
        if d["ma50"] is not None and d["close"] > d["ma50"]:
            score += 15
            reasons.append("Price > MA50")
        
        # --- 4. Price > MA20 ---
        if d["ma20"] is not None and d["close"] > d["ma20"]:
            score += 10
            reasons.append("Price > MA20")
        
        # --- 5. Volume ---
        vol_avg = self._get_volume_avg(ins_code, 20)
        if vol_avg > 0 and d["volume"] > vol_avg * 1.5:
            score += 15
            reasons.append(f"Volume {d['volume']/vol_avg:.1f}x avg")
        
        # --- 6. Bollinger ---
        if d["bb_lower"] is not None and d["bb_upper"] is not None:
            bb_width = (d["bb_upper"] - d["bb_lower"]) / d["bb_middle"] if d["bb_middle"] else 0
            if bb_width < 0.15:
                score += 10
                reasons.append("BB squeeze")
            if d["close"] <= d["bb_lower"] * 1.03:
                score += 10
                reasons.append("Near BB lower")
        
        # محدود کردن امتیاز بین 0 تا 100
        score = max(0, min(100, score))
        
        return {
            "ins_code": ins_code,
            "symbol": d["symbol"],
            "name": d["name"],
            "date": d["date"],
            "close": d["close"],
            "score": score,
            "reasons": reasons,
            "rsi": round(rsi, 1) if rsi else None,
            "macd": round(d["macd"], 2) if d["macd"] else None,
            "volume_ratio": round(d["volume"] / vol_avg, 2) if vol_avg else None,
        }

    def find_top_setups(self, min_score=50, limit=30):
        codes = self._get_all_codes()
        results = []
        for code in codes:
            r = self.score_symbol(code)
            if r and r["score"] >= min_score:
                results.append(r)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]


if __name__ == "__main__":
    print("=" * 70)
    print("SETUP FINDER - Multi-Indicator Confluence (FIXED)")
    print("=" * 70)
    
    finder = SetupFinder()
    results = finder.find_top_setups(min_score=40, limit=30)
    finder.close()
    
    print(f"Found {len(results)} symbols with score >= 40\n")
    print(f"{'#':>3} | {'Symbol':12s} | {'Score':>5s} | {'RSI':>6s} | {'Vol x':>6s} | Reasons")
    print("-" * 90)
    
    for i, r in enumerate(results, 1):
        reasons = ", ".join(r["reasons"][:3])
        rsi_str = f"{r['rsi']}" if r['rsi'] else "-"
        vol_str = f"{r['volume_ratio']}" if r['volume_ratio'] else "-"
        print(f"{i:>3} | {r['symbol'][:12]:12s} | {r['score']:>5d} | {rsi_str:>6} | {vol_str:>6} | {reasons}")
    
    out = Path("data/top_setups.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Saved to: {out}")
    print("=" * 70)
