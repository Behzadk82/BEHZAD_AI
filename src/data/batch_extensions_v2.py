# src/data/batch_extensions_v2.py
# پر کردن Volume Profile, Support/Resistance, Pivot Points

import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH
from src.analysis.extensions_v2 import compute_volume_profile, compute_support_resistance
from src.analysis.extensions_v3 import compute_pivot_points, compute_pivot_fibonacci


def main():
    print("=" * 60)
    print("BATCH EXTENSIONS V2 - Volume Profile + S/R + Pivot")
    print("=" * 60)
    
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    
    symbols = [r[0] for r in con.execute(
        "SELECT DISTINCT ins_code FROM indicators WHERE atr14 IS NOT NULL"
    ).fetchall()]
    print(f"تعداد نمادها: {len(symbols)}")
    
    saved_total = 0
    start = time.time()
    
    for idx, ins_code in enumerate(symbols, 1):
        try:
            rows = con.execute("""
                SELECT date, price_max, price_min, price_close, volume
                FROM price_history
                WHERE ins_code = ?
                ORDER BY date ASC
            """, (ins_code,)).fetchall()
            prices = [dict(r) for r in rows]
            
            if len(prices) < 60:
                continue
            
            # Volume Profile
            vp = compute_volume_profile(prices, days=60, bins=10)
            
            # Support/Resistance
            sr = compute_support_resistance(prices, lookback=50)
            
            # Pivot Points (روی آخرین روز)
            last = prices[-1]
            pivot = compute_pivot_points(last["price_max"], last["price_min"], last["price_close"])
            pivot_fib = compute_pivot_fibonacci(last["price_max"], last["price_min"], last["price_close"])
            
            # ذخیره روی آخرین رکورد
            with con:
                if vp:
                    con.execute("""
                        UPDATE indicators
                        SET vp_poc = ?, vp_va_low = ?, vp_va_high = ?
                        WHERE ins_code = ? AND date = ?
                    """, (vp["poc"], vp["value_area_low"], vp["value_area_high"], ins_code, last["date"]))
                
                if sr:
                    con.execute("""
                        UPDATE indicators
                        SET nearest_support = ?, nearest_resistance = ?
                        WHERE ins_code = ? AND date = ?
                    """, (sr["nearest_support"], sr["nearest_resistance"], ins_code, last["date"]))
                
                con.execute("""
                    UPDATE indicators
                    SET pivot = ?, pivot_r1 = ?, pivot_r2 = ?, pivot_r3 = ?,
                        pivot_s1 = ?, pivot_s2 = ?, pivot_s3 = ?,
                        pivot_fib_r1 = ?, pivot_fib_r2 = ?, pivot_fib_r3 = ?,
                        pivot_fib_s1 = ?, pivot_fib_s2 = ?, pivot_fib_s3 = ?
                    WHERE ins_code = ? AND date = ?
                """, (
                    pivot["pivot"], pivot["r1"], pivot["r2"], pivot["r3"],
                    pivot["s1"], pivot["s2"], pivot["s3"],
                    pivot_fib["r1"], pivot_fib["r2"], pivot_fib["r3"],
                    pivot_fib["s1"], pivot_fib["s2"], pivot_fib["s3"],
                    ins_code, last["date"],
                ))
                saved_total += 1
            
            if idx % 100 == 0 or idx <= 3:
                print(f"[{idx}/{len(symbols)}] OK")
        except Exception as e:
            print(f"[{idx}] ERROR: {type(e).__name__}: {e}")
    
    elapsed = time.time() - start
    con.close()
    
    print()
    print("=" * 60)
    print(f"DONE: {saved_total} symbols updated in {elapsed:.0f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
