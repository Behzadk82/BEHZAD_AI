# src/data/migrate_history.py
# Add price_history table and migrate JSON data to SQLite - Phase 1.2

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone


DB_PATH = Path("data/behzad_ai.db")
HISTORY_JSON = Path("data/history_FOLAD.json")
INS_CODE = "46348559193224090"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_history_table(con):
    con.executescript("""
        CREATE TABLE IF NOT EXISTS price_history (
            ins_code TEXT NOT NULL,
            date INTEGER NOT NULL,
            price_close REAL,
            price_last REAL,
            price_min REAL,
            price_max REAL,
            price_first REAL,
            price_yesterday REAL,
            price_change REAL,
            volume REAL,
            value REAL,
            trades REAL,
            source TEXT NOT NULL DEFAULT 'DailyList',
            inserted_at TEXT NOT NULL,
            PRIMARY KEY (ins_code, date)
        );

        CREATE INDEX IF NOT EXISTS idx_history_date ON price_history(date);
        CREATE INDEX IF NOT EXISTS idx_history_ins_code ON price_history(ins_code);
    """)


def upsert_history(con, ins_code: str, records: list) -> int:
    now = now_iso()
    count = 0
    with con:
        for r in records:
            con.execute("""
                INSERT INTO price_history (
                    ins_code, date, price_close, price_last,
                    price_min, price_max, price_first,
                    price_yesterday, price_change,
                    volume, value, trades, source, inserted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ins_code, date) DO UPDATE SET
                    price_close=excluded.price_close,
                    price_last=excluded.price_last,
                    price_min=excluded.price_min,
                    price_max=excluded.price_max,
                    price_first=excluded.price_first,
                    price_yesterday=excluded.price_yesterday,
                    price_change=excluded.price_change,
                    volume=excluded.volume,
                    value=excluded.value,
                    trades=excluded.trades,
                    source=excluded.source,
                    inserted_at=excluded.inserted_at
            """, (
                ins_code, r["date"], r["price_close"], r["price_last"],
                r["price_min"], r["price_max"], r["price_first"],
                r["price_yesterday"], r["price_change"],
                r["volume"], r["value"], r["trades"],
                "DailyList", now,
            ))
            count += 1
    return count


def main():
    print("=" * 60)
    print("HISTORY MIGRATION TO SQLITE")
    print("=" * 60)

    if not DB_PATH.exists():
        print(f"[ERROR] {DB_PATH} not found. Run database.py first.")
        return

    if not HISTORY_JSON.exists():
        print(f"[ERROR] {HISTORY_JSON} not found. Run history.py first.")
        return

    with HISTORY_JSON.open("r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"Loaded {len(records)} records from {HISTORY_JSON}")

    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")

    print("Initializing price_history table...")
    init_history_table(con)

    print(f"Upserting {len(records)} records for ins_code={INS_CODE}...")
    count = upsert_history(con, INS_CODE, records)
    print(f"Upserted: {count} rows")

    # Stats
    total = con.execute("SELECT COUNT(*) FROM price_history").fetchone()[0]
    unique_dates = con.execute("SELECT COUNT(DISTINCT date) FROM price_history").fetchone()[0]
    min_date = con.execute("SELECT MIN(date) FROM price_history").fetchone()[0]
    max_date = con.execute("SELECT MAX(date) FROM price_history").fetchone()[0]

    print()
    print("Database stats:")
    print(f"  total rows in price_history: {total}")
    print(f"  unique dates: {unique_dates}")
    print(f"  date range: {min_date} -> {max_date}")

    # Show last 3 rows
    print()
    print("Last 3 rows (FOLAD):")
    rows = con.execute(
        "SELECT date, price_close, volume, trades FROM price_history "
        "WHERE ins_code = ? ORDER BY date DESC LIMIT 3",
        (INS_CODE,)
    ).fetchall()
    for r in rows:
        print(f"  {r['date']} | close={r['price_close']} | vol={int(r['volume'])} | trades={int(r['trades'])}")

    # Verify specific date
    print()
    print("Verify 20261124 (last day):")
    row = con.execute(
        "SELECT * FROM price_history WHERE ins_code = ? AND date = ?",
        (INS_CODE, 20261124)
    ).fetchone()
    if row:
        print(f"  close = {row['price_close']}")
        print(f"  volume = {row['volume']}")
        print(f"  trades = {row['trades']}")
    else:
        print("  NOT FOUND")

    con.close()

    db_size = round(DB_PATH.stat().st_size / 1024, 1)
    print()
    print(f"DB size: {db_size} KB")
    print("=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
