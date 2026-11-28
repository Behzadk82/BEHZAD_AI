# src/data/multi_timeframe_builder.py
import sqlite3, sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

def init_tables(con):
    con.executescript("""
        CREATE TABLE IF NOT EXISTS price_history_weekly (
            ins_code TEXT, week_start INTEGER, price_open REAL, price_high REAL, price_low REAL, price_close REAL,
            volume REAL, value REAL, trades REAL, PRIMARY KEY (ins_code, week_start)
        );
        CREATE TABLE IF NOT EXISTS price_history_monthly (
            ins_code TEXT, month_start INTEGER, price_open REAL, price_high REAL, price_low REAL, price_close REAL,
            volume REAL, value REAL, trades REAL, PRIMARY KEY (ins_code, month_start)
        );
    """)
    con.commit()

def aggregate(rows):
    rows.sort(key=lambda x: x["date"])
    return {
        "open": rows[0]["price_close"], "high": max(r["price_max"] for r in rows),
        "low": min(r["price_min"] for r in rows), "close": rows[-1]["price_close"],
        "volume": sum(r["volume"] for r in rows), "value": sum(r["value"] for r in rows),
        "trades": sum(r["trades"] for r in rows)
    }

def main():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    init_tables(con)
    symbols = [r[0] for r in con.execute("SELECT DISTINCT ins_code FROM price_history").fetchall()]
    
    for idx, code in enumerate(symbols, 1):
        rows = con.execute("SELECT date, price_close, price_max, price_min, volume, value, trades FROM price_history WHERE ins_code=? ORDER BY date ASC", (code,)).fetchall()
        if len(rows) < 10: continue
        
        groups_w = {}
        groups_m = {}
        for r in rows:
            dt_str = str(r["date"])
            try:
                dt = datetime.strptime(dt_str, "%Y%m%d")
                y, w, _ = dt.isocalendar()
                groups_w.setdefault(y*100+w, []).append(r)
                groups_m.setdefault(int(dt_str[:6]), []).append(r)
            except: continue
            
        for k, rs in groups_w.items():
            a = aggregate(rs)
            con.execute("INSERT OR REPLACE INTO price_history_weekly VALUES (?,?,?,?,?,?,?,?,?)", (code, k, a["open"], a["high"], a["low"], a["close"], a["volume"], a["value"], a["trades"]))
        for k, rs in groups_m.items():
            a = aggregate(rs)
            con.execute("INSERT OR REPLACE INTO price_history_monthly VALUES (?,?,?,?,?,?,?,?,?)", (code, k, a["open"], a["high"], a["low"], a["close"], a["volume"], a["value"], a["trades"]))
        
        if idx % 100 == 0: print(f"[{idx}/{len(symbols)}] OK")
    con.commit(); con.close()
    print("DONE")

if __name__ == "__main__":
    main()
