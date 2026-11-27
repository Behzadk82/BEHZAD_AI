# src/data/batch_indicators.py
# Recompute indicators for symbols with missing history dates.
# Existing database schema and storage paths are preserved.

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import DB_PATH
from src.analysis.indicators import Indicators


def get_symbols_with_history(con):
    rows = con.execute(
        """
        SELECT DISTINCT ins_code
        FROM price_history
        WHERE ins_code IS NOT NULL
        ORDER BY ins_code
        """
    ).fetchall()
    return [r["ins_code"] for r in rows]


def get_pending_symbols(con):
    """
    Return symbols having at least one history date without indicators.
    This detects new dates as well as missing indicator rows.
    """
    rows = con.execute(
        """
        SELECT DISTINCT p.ins_code
        FROM price_history AS p
        LEFT JOIN indicators AS i
          ON i.ins_code = p.ins_code
         AND i.date = p.date
        WHERE i.ins_code IS NULL
        ORDER BY p.ins_code
        """
    ).fetchall()
    return [r["ins_code"] for r in rows]


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def compute_and_save(con, ins_code):
    """Recompute indicators from full history and upsert valid rows."""
    ind = Indicators(ins_code)
    count = ind.load_from_db()

    if count == 0:
        return 0

    ma5 = ind.sma(5)
    ma10 = ind.sma(10)
    ma20 = ind.sma(20)
    ma50 = ind.sma(50)
    rsi14 = ind.rsi(14)
    macd_data = ind.macd()
    bb = ind.bollinger()

    now = now_iso()
    changed = 0

    with con:
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


            cursor = con.execute(
                """
                INSERT INTO indicators (
                    ins_code, date,
                    ma5, ma10, ma20, ma50,
                    rsi14,
                    macd, macd_signal, macd_histogram,
                    bb_upper, bb_middle, bb_lower,
                    computed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                """,
                (
                    ins_code,
                    row["date"],
                    row["ma5"],
                    row["ma10"],
                    row["ma20"],
                    row["ma50"],
                    row["rsi14"],
                    row["macd"],
                    row["macd_signal"],
                    row["macd_histogram"],
                    row["bb_upper"],
                    row["bb_middle"],
                    row["bb_lower"],
                    now,
                ),
            )

            if cursor.rowcount > 0:
                changed += 1

    return changed


def main():
    print("=" * 70)
    print("BATCH INDICATORS - Missing history dates")
    print("=" * 70)

    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row

    try:
        con.execute("PRAGMA journal_mode=WAL")

        symbols = get_symbols_with_history(con)
        pending = get_pending_symbols(con)

        print(f"Total symbols with history: {len(symbols)}")
        print(f"Symbols needing computation: {len(pending)}")
        print()

        if not pending:
            print("All history dates already have indicator rows.")
            return

        success = 0
        failed = 0
        total_rows = 0

        for i, ins_code in enumerate(pending, 1):
            print(f"[{i}/{len(pending)}] {ins_code}...", end=" ")

            try:
                saved = compute_and_save(con, ins_code)

                if saved > 0:
                    success += 1
                    total_rows += saved
                    print(f"OK - {saved} rows affected")
                else:
                    failed += 1
                    print("NO DATA / NO INDICATORS")

            except Exception as exc:
                failed += 1
                print(f"ERROR - {type(exc).__name__}: {exc}")

        total_indicators = con.execute(
            "SELECT COUNT(*) FROM indicators"
        ).fetchone()[0]

        indicator_symbols = con.execute(
            "SELECT COUNT(DISTINCT ins_code) FROM indicators"
        ).fetchone()[0]

        print()
        print("=" * 70)
        print("BATCH INDICATORS COMPLETE")
        print(f"  Success: {success}")
        print(f"  Failed: {failed}")
        print(f"  Rows affected: {total_rows}")
        print(f"  Indicator rows in DB: {total_indicators}")
        print(f"  Symbols with indicators: {indicator_symbols}")
        print("=" * 70)

    finally:
        con.close()


if __name__ == "__main__":
    main()
