import sqlite3, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH
from src.analysis.extensions_v1 import compute_rvol, compute_stoch_rsi, compute_wma, compute_vwma, compute_aroon

def main():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    symbols = [r[0] for r in con.execute("SELECT DISTINCT ins_code FROM indicators WHERE atr14 IS NOT NULL").fetchall()]
    print(f"Total: {len(symbols)}")
    saved = 0
    for idx, ins_code in enumerate(symbols, 1):
        try:
            rows = con.execute("""SELECT p.date, p.price_max, p.price_min, p.price_close, p.volume, i.rsi14
                FROM price_history p JOIN indicators i ON p.ins_code = i.ins_code AND p.date = i.date
                WHERE p.ins_code = ? ORDER BY p.date ASC""", (ins_code,)).fetchall()
            prices = [dict(r) for r in rows]
            if len(prices) < 50: continue
            rsi_list = [p["rsi14"] for p in prices]
            rvol = compute_rvol(prices)
            stoch_rsi = compute_stoch_rsi(rsi_list)
            wma = compute_wma(prices, 20)
            vwma = compute_vwma(prices, 20)
            aroon = compute_aroon(prices, 25)
            with con:
                for i, p in enumerate(prices):
                    con.execute("""UPDATE indicators SET rvol=?, stoch_rsi=?, wma20=?, vwma20=?, aroon_up=?, aroon_down=?, aroon_osc=?
                        WHERE ins_code=? AND date=?""", (rvol[i], stoch_rsi[i], wma[i], vwma[i], aroon["aroon_up"][i], aroon["aroon_down"][i], aroon["aroon_osc"][i], ins_code, p["date"]))
                    saved += 1
            if idx % 100 == 0: print(f"[{idx}/{len(symbols)}] OK")
        except Exception as e: print(f"[{idx}] ERROR: {e}")
    con.close()
    print(f"DONE: {saved} rows")

if __name__ == "__main__":
    main()
