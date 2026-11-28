# src/data/intraday_fetcher.py
import sys, sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

try:
    from yfinance_ir import Ticker
except ImportError:
    print("yfinance-ir not installed. Run: pip install yfinance-ir")
    sys.exit(1)

ALL_INTERVALS = {
    "1m": {"period": "5d", "name": "1 دقیقه"},
    "5m": {"period": "1mo", "name": "5 دقیقه"},
    "15m": {"period": "1mo", "name": "15 دقیقه"},
    "30m": {"period": "3mo", "name": "30 دقیقه"},
    "1h": {"period": "3mo", "name": "1 ساعت"},
    "4h": {"period": "6mo", "name": "4 ساعت"},
}

def init_intraday_table(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS price_history_intraday (
            ins_code TEXT NOT NULL, interval TEXT NOT NULL, datetime TEXT NOT NULL,
            price_open REAL, price_high REAL, price_low REAL, price_close REAL, volume REAL,
            PRIMARY KEY (ins_code, interval, datetime)
        )
    """)
    con.commit()

def fetch_intraday(symbol_name, interval, period):
    try:
        t = Ticker(symbol_name)
        hist = t.history(period=period, interval=interval)
        return hist if hist is not None and not hist.empty else None
    except Exception:
        return None

def save_intraday(con, ins_code, interval, hist):
    saved = 0
    with con:
        for idx, row in hist.iterrows():
            try:
                con.execute("""
                    INSERT OR REPLACE INTO price_history_intraday
                    (ins_code, interval, datetime, price_open, price_high, price_low, price_close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (ins_code, interval, str(idx), float(row.get("Open",0)), float(row.get("High",0)),
                      float(row.get("Low",0)), float(row.get("Close",0)), float(row.get("Volume",0))))
                saved += 1
            except Exception:
                continue
    return saved

def main():
    print("INTRADAY FETCHER")
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.execute("PRAGMA journal_mode=WAL")
    init_intraday_table(con)
    symbols = con.execute("SELECT ins_code, symbol FROM symbols LIMIT 20").fetchall()
    for interval, config in ALL_INTERVALS.items():
        print(f"\n{config['name']} ({interval})...")
        for ins_code, symbol in symbols:
            hist = fetch_intraday(symbol, interval, config["period"])
            if hist is not None:
                saved = save_intraday(con, ins_code, interval, hist)
                print(f"  {symbol}: {saved} candles")
            else:
                print(f"  {symbol}: no data")
    con.close()
    print("DONE")

if __name__ == "__main__":
    main()
