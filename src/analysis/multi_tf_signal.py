# src/analysis/multi_tf_signal.py
import sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

def get_multi_tf_signal(ins_code):
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    
    daily = con.execute("""
        SELECT i.supertrend_direction, i.rsi14, i.adx14 FROM indicators i 
        WHERE ins_code=? ORDER BY date DESC LIMIT 1
    """, (ins_code,)).fetchone()
    weekly = con.execute("SELECT supertrend_direction, rsi14 FROM indicators_weekly WHERE ins_code=? ORDER BY date DESC LIMIT 1", (ins_code,)).fetchone()
    monthly = con.execute("SELECT supertrend_direction, rsi14 FROM indicators_monthly WHERE ins_code=? ORDER BY date DESC LIMIT 1", (ins_code,)).fetchone()
    sym = con.execute("SELECT symbol FROM symbols WHERE ins_code=?", (ins_code,)).fetchone()
    con.close()
    
    if not daily or not sym: return None
    
    score = 0; reasons = []
    
    # روزانه
    if daily["supertrend_direction"] == "UP": score += 20; reasons.append("Supertrend روزانه صعودی")
    else: score -= 20
    if daily["rsi14"] and daily["rsi14"] < 50: score += 15; reasons.append(f"RSI روزانه {daily['rsi14']:.0f}")
    if daily["adx14"] and daily["adx14"] > 25: score += 10; reasons.append(f"ADX {daily['adx14']:.0f}")
    
    # هفتگی
    if weekly:
        if weekly["supertrend_direction"] == "UP": score += 20; reasons.append("Supertrend هفتگی صعودی")
        else: score -= 15
        if weekly["rsi14"] and weekly["rsi14"] < 50: score += 15
    
    # ماهانه
    if monthly:
        if monthly["supertrend_direction"] == "UP": score += 20; reasons.append("Supertrend ماهانه صعودی")
        if monthly["rsi14"] and monthly["rsi14"] < 50: score += 10
    
    score = max(0, min(100, score))
    
    return {"symbol": sym["symbol"], "score": score, "reasons": reasons, "daily": dict(daily) if daily else None, "weekly": dict(weekly) if weekly else None, "monthly": dict(monthly) if monthly else None}

def scan_all():
    con = sqlite3.connect(DB_PATH, timeout=15)
    symbols = [r[0] for r in con.execute("SELECT DISTINCT ins_code FROM indicators_weekly").fetchall()]
    con.close()
    results = []
    for code in symbols:
        r = get_multi_tf_signal(code)
        if r and r["score"] >= 50: results.append(r)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

if __name__ == "__main__":
    print("MULTI-TIMEFRAME SIGNAL TEST")
    for code in ["46348559193224090", "35425587644337450"]:
        r = get_multi_tf_signal(code)
        if r: print(f"{r['symbol']}: Score={r['score']}, Reasons={', '.join(r['reasons'][:3])}")
    print("\nSCANNING...")
    results = scan_all()
    print(f"Found {len(results)} symbols with score >= 50")
    for r in results[:10]:
        print(f"  {r['symbol']}: {r['score']}")
