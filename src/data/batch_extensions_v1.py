# src/data/batch_extensions_v1.py
import sqlite3, sys, time
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH
from src.analysis.extensions_v1 import compute_supertrend, compute_rvol, compute_stoch_rsi, compute_wma, compute_vwma, compute_aroon

def main():
    print("=" * 60)
    print("BATCH EXTENSIONS V1")
    print("=" * 60)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    
    symbols = [r[0] for r in con.execute("SELECT DISTINCT ins_code FROM indicators WHERE atr14 IS NOT NULL").fetchall()]
    print(f"تعداد نمادها: {len(symbols)}")
    
    saved_total = 0
    start = time.time()
    
    for idx, ins_code in enumerate(symbols, 1):
        try:
            rows = con.execute("""SELECT p.date, p.price_max, p.price_min, p.price_close, p.volume, i.atr14
                FROM price_history p JOIN indicators i ON p.ins_code=i.ins_code AND p.date=i.date
                WHERE p.ins_code = ? ORDER BY p.date ASC""", (ins_code,)).fetchall()
            prices = [dict(r) for r in rows]
            if len(prices) < 50: continue
            
            atr = [p["atr14"] for p in prices]
            st = compute_supertrend(prices, atr)
            
            with con:
                for i, p in enumerate(prices):
                    if st["supertrend"][i] is None: continue
                    con.execute("""UPDATE indicators SET supertrend=?, supertrend_direction=?, supertrend_upper=?, supertrend_lower=?
                        WHERE ins_code=? AND date=?""",
                        (st["supertrend"][i], st["direction"][i], st["upper"][i], st["lower"][i], ins_code, p["date"]))
                    saved_total += 1
            
            if idx % 100 == 0 or idx <= 3:
                print(f"[{idx}/{len(symbols)}] OK")
        except Exception as e:
            print(f"[{idx}] ERROR: {e}")
    
    elapsed = time.time() - start
    con.close()
    print(f"\nDONE: {saved_total} rows in {elapsed:.0f}s")

if __name__ == "__main__":
    main()
