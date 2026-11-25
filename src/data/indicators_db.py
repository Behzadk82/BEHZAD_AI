# src/data/indicators_db.py
# Store computed indicators in SQLite - Phase 2.2

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH
from src.analysis.indicators import Indicators


INS_CODE = "46348559193224090"
SYMBOL = "FOLAD"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_indicators_table(con):
    con.executescript("""
        CREATE TABLE IF NOT EXISTS indicators (
            ins_code TEXT NOT NULL,
            date INTEGER NOT NULL,
            ma5 REAL,
            ma10 REAL,
            ma20 REAL,
            ma50 REAL,
            rsi14 REAL,
            macd REAL,
            macd_signal REAL,
            macd_histogram REAL,
            bb_upper REAL,
            bb_middle REAL,
            bb_lower REAL,
            computed_at TEXT NOT NULL,
            PRIMARY KEY (ins_code, date)
        );
        
        CREATE INDEX IF NOT EXISTS idx_ind_date ON indicators(date);
        CREATE INDEX IF NOT EXISTS idx_ind_ins_code ON indicators(ins_code);
    """)


def upsert_indicators(con, ins_code: str, rows: list) -> int:
    """rows = list of dicts with keys: date, ma5, ma20, rsi14, etc."""
    now = now_iso()
    count = 0
    with con:
        for r in rows:
            con.execute("""
                INSERT INTO indicators (
                    ins_code, date, ma5, ma10, ma20, ma50,
                    rsi14, macd, macd_signal, macd_histogram,
                    bb_upper, bb_middle, bb_lower, computed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ins_code, date) DO UPDATE SET
                    ma5=excluded.ma5,
                    ma10=excluded.ma10,
                    ma20=excluded.ma20,
                    ma50=excluded.ma50,
                    rsi14=excluded.rsi14,
                    macd=excluded.macd,
                    macd_signal=excluded.macd_signal,
                    macd_histogram=excluded.macd_histogram,
                    bb_upper=excluded.bb_upper,
                    bb_middle=excluded.bb_middle,
                    bb_lower=excluded.bb_lower,
                    computed_at=excluded.computed_at
            """, (
                ins_code, r["date"], r.get("ma5"), r.get("ma10"),
                r.get("ma20"), r.get("ma50"), r.get("rsi14"),
                r.get("macd"), r.get("macd_signal"), r.get("macd_histogram"),
                r.get("bb_upper"), r.get("bb_middle"), r.get("bb_lower"),
                now,
            ))
            count += 1
    return count


def compute_all_indicators(ins_code: str) -> list:
    """Compute indicators for every day in the history."""
    ind = Indicators(ins_code)
    count = ind.load_from_db()
    if count == 0:
        return []
    
    # Compute all series
    ma5 = ind.sma(5)
    ma10 = ind.sma(10)
    ma20 = ind.sma(20)
    ma50 = ind.sma(50)
    rsi14 = ind.rsi(14)
    macd_data = ind.macd()
    bb = ind.bollinger()
    
    rows = []
    for i in range(count):
        row = {
            "date": ind.prices[i]["date"],
            "ma5": ma5[i],
            "ma10": ma10[i],
            "ma20": ma20[i],
            "ma50": ma50[i],
            "rsi14": rsi14[i],
            "macd": macd_data["macd"][i],
            "macd_signal": macd_data["signal"][i],
            "macd_histogram": macd_data["histogram"][i],
            "bb_upper": bb["upper"][i],
            "bb_middle": bb["middle"][i],
            "bb_lower": bb["lower"][i],
        }
        rows.append(row)
    
    return rows


def main():
    print("=" * 60)
    print("INDICATORS MIGRATION TO SQLITE")
    print("=" * 60)
    
    if not DB_PATH.exists():
        print(f"[ERROR] {DB_PATH} not found")
        return
    
    print(f"Computing indicators for {SYMBOL} ({INS_CODE})...")
    rows = compute_all_indicators(INS_CODE)
    
    if not rows:
        print("[ERROR] No data")
        return
    
    print(f"Computed {len(rows)} rows")
    
    # Filter out rows where all indicators are None (early days)
    valid_rows = []
    for r in rows:
        has_data = any(v is not None for k, v in r.items() if k != "date")
        if has_data:
            valid_rows.append(r)
    
    print(f"Rows with at least one indicator: {len(valid_rows)}")
    
    # Store
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    
    print("Initializing indicators table...")
    init_indicators_table(con)
    
    print(f"Upserting {len(valid_rows)} rows...")
    count = upsert_indicators(con, INS_CODE, valid_rows)
    print(f"Upserted: {count} rows")
    
    # Stats
    total = con.execute("SELECT COUNT(*) FROM indicators").fetchone()[0]
    min_date = con.execute("SELECT MIN(date) FROM indicators WHERE ins_code = ?", (INS_CODE,)).fetchone()[0]
    max_date = con.execute("SELECT MAX(date) FROM indicators WHERE ins_code = ?", (INS_CODE,)).fetchone()[0]
    
    print()
    print("Database stats (indicators):")
    print(f"  total rows: {total}")
    print(f"  date range: {min_date} -> {max_date}")
    
    # Show latest
    print()
    print("Latest indicator row (FOLAD):")
    row = con.execute(
        "SELECT * FROM indicators WHERE ins_code = ? ORDER BY date DESC LIMIT 1",
        (INS_CODE,)
    ).fetchone()
    if row:
        for k in ("date", "ma5", "ma20", "rsi14", "macd", "macd_signal", "bb_upper", "bb_lower"):
            v = row[k]
            if isinstance(v, float):
                print(f"  {k:15s} = {v:.2f}")
            else:
                print(f"  {k:15s} = {v}")
    
    con.close()
    
    db_size = round(DB_PATH.stat().st_size / 1024, 1)
    print()
    print(f"DB size: {db_size} KB")
    print("=" * 60)
    print("INDICATORS MIGRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
