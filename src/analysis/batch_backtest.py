# src/analysis/batch_backtest.py
# Run all strategies on all symbols and rank them.

import sqlite3
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH
from src.analysis.backtest import Backtest


def get_all_ins_codes():
    con = sqlite3.connect(DB_PATH, timeout=15)
    rows = con.execute("SELECT DISTINCT ins_code FROM indicators").fetchall()
    con.close()
    return [r[0] for r in rows]


def get_symbol_name(ins_code):
    con = sqlite3.connect(DB_PATH, timeout=15)
    row = con.execute("SELECT symbol FROM symbols WHERE ins_code = ?", (ins_code,)).fetchone()
    con.close()
    return row[0] if row else "?"


def main():
    print("=" * 70)
    print("BATCH BACKTEST - All Symbols, All Strategies")
    print("=" * 70)

    codes = get_all_ins_codes()
    print(f"Testing {len(codes)} symbols...")
    print()

    results = []

    for i, code in enumerate(codes, 1):
        symbol = get_symbol_name(code)
        bt = Backtest(code, initial_capital=100_000_000)
        
        try:
            r_macd = bt.run_macd()
            r_ma = bt.run_ma_cross()
        except Exception:
            r_macd, r_ma = None, None
        finally:
            bt.close()

        if r_macd and r_ma:
            best = r_macd if r_macd["total_return_pct"] > r_ma["total_return_pct"] else r_ma
            results.append({
                "ins_code": code,
                "symbol": symbol,
                "macd_return": r_macd["total_return_pct"],
                "macd_dd": r_macd["max_drawdown_pct"],
                "macd_trades": r_macd["total_trades"],
                "ma_return": r_ma["total_return_pct"],
                "ma_dd": r_ma["max_drawdown_pct"],
                "ma_trades": r_ma["total_trades"],
                "best_strategy": "MACD" if best is r_macd else "MA_CROSS",
                "best_return": best["total_return_pct"],
            })

        if i % 50 == 0:
            print(f"  Progress: {i}/{len(codes)}")

    # Sort by best return
    results.sort(key=lambda x: x["best_return"], reverse=True)

    print()
    print("=" * 70)
    print("TOP 20 BEST PERFORMERS")
    print("=" * 70)
    print(f"{'#':>3} | {'Symbol':15s} | {'Best Strategy':12s} | {'Return':>12s} | {'MaxDD':>8s} | {'Trades':>6s}")
    print("-" * 70)
    for i, r in enumerate(results[:20], 1):
        print(f"{i:>3} | {r['symbol'][:15]:15s} | {r['best_strategy']:12s} | {r['best_return']:>11.1f}% | {r['best_dd'] if 'best_dd' in r else (r['macd_dd'] if r['best_strategy']=='MACD' else r['ma_dd']):>7.1f}% | {r['macd_trades'] if r['best_strategy']=='MACD' else r['ma_trades']:>6}")

    # Save
    out = Path("data/backtest_results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print()
    print(f"✅ Results saved to: {out}")
    print(f"   Total symbols: {len(results)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
