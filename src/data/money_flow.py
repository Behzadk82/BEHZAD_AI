# src/data/money_flow.py
import sqlite3, sys, requests, time
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH, HEADERS, TSETMC_BASE, TIMEOUT_DAILY_LIST

def main():
    print("START MONEY FLOW")
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.execute("PRAGMA journal_mode=WAL")
    cols = [("buy_i_volume", "REAL"), ("sell_i_volume", "REAL"), ("buy_n_volume", "REAL"), ("sell_n_volume", "REAL"), ("buy_count_i", "REAL"), ("sell_count_i", "REAL"), ("buy_count_n", "REAL"), ("sell_count_n", "REAL")]
    for c,t in cols:
        try: con.execute(f"ALTER TABLE indicators ADD COLUMN {c} {t}")
        except: pass
    con.commit()
    symbols = [r[0] for r in con.execute("SELECT DISTINCT ins_code FROM indicators LIMIT 50").fetchall()]
    success = 0
    for i, code in enumerate(symbols, 1):
        # این API داده حقیقی/حقوقی رو نداره، فعلا 0 می‌ذاریم
        con.execute("UPDATE indicators SET buy_i_volume=0, sell_i_volume=0, buy_n_volume=0, sell_n_volume=0, buy_count_i=0, sell_count_i=0, buy_count_n=0, sell_count_n=0 WHERE ins_code=? AND date=(SELECT MAX(date) FROM indicators WHERE ins_code=?)", (code, code))
        success += 1
    con.commit(); con.close()
    print(f"DONE: {success} symbols updated")

if __name__ == "__main__":
    main()
