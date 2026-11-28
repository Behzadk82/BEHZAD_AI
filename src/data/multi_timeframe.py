# src/data/multi_timeframe.py
# تبدیل داده‌های روزانه به هفتگی و ماهانه
import sqlite3, sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

def init_tables(con):
    con.executescript("""
        CREATE TABLE IF NOT EXISTS price_history_weekly (
            ins_code TEXT, week_start INTEGER,
            price_open REAL, price_high REAL, price_low REAL, price_close REAL,
            volume REAL, value REAL, trades REAL,
            PRIMARY KEY (ins_code, week_start)
        );
        CREATE TABLE IF NOT EXISTS price_history_monthly (
            ins_code TEXT, month_start INTEGER,
            price_open REAL, price_high REAL, price_low REAL, price_close REAL,
            volume REAL, value REAL, trades REAL,
            PRIMARY KEY (ins_code, month_start)
        );
    """)
    con.commit()

def group_by_week(rows):
    """گروه‌بندی روزانه به هفتگی (بر اساس شماره هفته ISO)"""
    groups = {}
    for r in rows:
        date_str = str(r["date"])
        try:
            dt = datetime.strptime(date_str, "%Y%m%d")
            year, week, _ = dt.isocalendar()
            key = year * 100 + week
            if key not in groups:
                groups[key] = []
            groups[key].append(r)
        except:
            continue
    return groups

def group_by_month(rows):
    """گروه‌بندی روزانه به ماهانه"""
    groups = {}
    for r in rows:
        date_str = str(r["date"])
        try:
            key = int(date_str[:6])  # YYYYMM
            if key not in groups:
                groups[key] = []
            groups[key].append(r)
        except:
            continue
    return groups

def aggregate(group_rows):
    """تبدیل چند روز به یک کندل"""
    group_rows.sort(key=lambda x: x["date"])
    return {
        "open": group_rows[0]["price_close"],
        "high": max(r["price_max"] for r in group_rows),
        "low": min(r["price_min"] for r in group_rows),
        "close": group_rows[-1]["price_close"],
        "volume": sum(r["volume"] for r in group_rows),
        "value": sum(r["value"] for r in group_rows),
        "trades": sum(r["trades"] for r in group_rows),
    }

def main():
    print("=" * 60)
    print("MULTI-TIMEFRAME BUILDER")
    print("=" * 60)
    
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    init_tables(con)
    
    symbols = [r[0] for r in con.execute("SELECT DISTINCT ins_code FROM price_history").fetchall()]
    print(f"تعداد نمادها: {len(symbols)}")
    
    for idx, code in enumerate(symbols, 1):
        rows = con.execute("""
            SELECT date, price_close, price_max, price_min, volume, value, trades
            FROM price_history WHERE ins_code = ? ORDER BY date ASC
        """, (code,)).fetchall()
        
        if len(rows) < 10: continue
        
        # هفتگی
        weekly = group_by_week(rows)
        for week_key, w_rows in weekly.items():
            agg = aggregate(w_rows)
            con.execute("""
                INSERT OR REPLACE INTO price_history_weekly
                (ins_code, week_start, price_open, price_high, price_low, price_close, volume, value, trades)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (code, week_key, agg["open"], agg["high"], agg["low"], agg["close"], agg["volume"], agg["value"], agg["trades"]))
        
        # ماهانه
        monthly = group_by_month(rows)
        for month_key, m_rows in monthly.items():
            agg = aggregate(m_rows)
            con.execute("""
                INSERT OR REPLACE INTO price_history_monthly
                (ins_code, month_start, price_open, price_high, price_low, price_close, volume, value, trades)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (code, month_key, agg["open"], agg["high"], agg["low"], agg["close"], agg["volume"], agg["value"], agg["trades"]))
        
        if idx % 100 == 0:
            print(f"[{idx}/{len(symbols)}] OK")
    
    con.commit()
    con.close()
    print("✅ هفتگی و ماهانه ساخته شد.")

if __name__ == "__main__":
    main()
