# src/analysis/pro_scanner.py
import sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

class ProScanner:
    def __init__(self):
        self.con = sqlite3.connect(DB_PATH, timeout=15)
        self.con.row_factory = sqlite3.Row

    def close(self): self.con.close()

    def scan(self, min_score=50, limit=30):
        symbols = [r[0] for r in self.con.execute("SELECT DISTINCT ins_code FROM indicators WHERE supertrend IS NOT NULL").fetchall()]
        results = []
        
        for code in symbols:
            row = self.con.execute("""
                SELECT p.date, p.price_close, p.volume,
                    i.rsi14, i.macd, i.macd_signal, i.ma20, i.ma50,
                    i.supertrend, i.supertrend_direction, i.adx14, i.plus_di, i.minus_di,
                    i.rvol, i.stoch_rsi, i.aroon_up, i.aroon_down, i.aroon_osc,
                    i.bb_upper, i.bb_lower, i.obv, i.mfi14
                FROM price_history p JOIN indicators i ON p.ins_code=i.ins_code AND p.date=i.date
                WHERE p.ins_code = ? ORDER BY p.date DESC LIMIT 1
            """, (code,)).fetchone()
            
            if not row: continue
            
            sym = self.con.execute("SELECT symbol, name FROM symbols WHERE ins_code = ?", (code,)).fetchone()
            if not sym: continue
            
            score = 0; reasons = []; warnings = []
            
            # ۱. Supertrend
            if row["supertrend_direction"] == "UP":
                score += 20; reasons.append("Supertrend صعودی")
            else:
                warnings.append("Supertrend نزولی")
            
            # ۲. RSI
            if row["rsi14"]:
                if 30 <= row["rsi14"] <= 50:
                    score += 15; reasons.append(f"RSI({row['rsi14']:.0f}) در محدوده خرید")
                elif row["rsi14"] > 70:
                    score -= 15; warnings.append(f"RSI({row['rsi14']:.0f}) اشباع خرید")
            
            # ۳. MACD
            if row["macd"] and row["macd_signal"] and row["macd"] > row["macd_signal"]:
                score += 10; reasons.append("MACD صعودی")
            
            # ۴. روند
            if row["ma20"] and row["ma50"] and row["price_close"] > row["ma20"] > row["ma50"]:
                score += 15; reasons.append("روند کامل")
            
            # ۵. ADX
            if row["adx14"] and row["adx14"] > 25 and row["plus_di"] and row["minus_di"] and row["plus_di"] > row["minus_di"]:
                score += 10; reasons.append(f"ADX({row['adx14']:.0f}) صعودی")
            
            # ۶. RVOL
            if row["rvol"] and row["rvol"] > 1.5:
                score += 10; reasons.append(f"حجم {row['rvol']:.1f}x")
            
            # ۷. Stoch RSI
            if row["stoch_rsi"]:
                if row["stoch_rsi"] < 20:
                    score += 10; reasons.append(f"Stoch RSI({row['stoch_rsi']:.0f}) اشباع فروش")
                elif row["stoch_rsi"] > 80:
                    score -= 10; warnings.append(f"Stoch RSI({row['stoch_rsi']:.0f}) اشباع خرید")
            
            # ۸. Aroon
            if row["aroon_up"] and row["aroon_down"] and row["aroon_up"] > row["aroon_down"]:
                score += 10; reasons.append("Aroon صعودی")
            
            score = max(0, min(100, score))
            
            if score >= min_score:
                results.append({
                    "ins_code": code, "symbol": sym["symbol"], "name": sym["name"],
                    "close": row["price_close"], "score": score,
                    "reasons": reasons, "warnings": warnings,
                    "rsi": round(row["rsi14"], 1) if row["rsi14"] else None,
                    "adx": round(row["adx14"], 1) if row["adx14"] else None,
                })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

if __name__ == "__main__":
    print("PRO SCANNER")
    s = ProScanner()
    res = s.scan(min_score=40, limit=20)
    s.close()
    print(f"Found {len(res)} symbols:\n")
    for i, r in enumerate(res, 1):
        print(f"{i}. {r['symbol']} | Score={r['score']} | RSI={r['rsi']} | {' ,'.join(r['reasons'][:2])}")
