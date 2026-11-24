# src/data/database.py
# SQLite storage for BEHZAD_AI - Phase 1.1.3
# Uses WAL mode for better concurrency, atomic transactions.

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


DB_PATH = Path("data/behzad_ai.db")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    """SQLite wrapper for BEHZAD_AI project"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path, timeout=15)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_schema(self):
        """Create tables if not exist."""
        con = self.conn or self.connect()
        con.executescript("""
            CREATE TABLE IF NOT EXISTS symbols (
                ins_code TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                name TEXT,
                last_price REAL,
                close_price REAL,
                yesterday_price REAL,
                volume REAL,
                value REAL,
                trades REAL,
                eps REAL,
                pe REAL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS fetch_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                record_count INTEGER NOT NULL,
                notes TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_symbols_symbol ON symbols(symbol);
        """)
        con.commit()
        print(f"[DB] Schema initialized at {self.db_path}")

    def upsert_symbols(self, symbols: List[Dict[str, Any]]) -> int:
        """Insert or update symbols. Returns number of rows affected."""
        con = self.conn or self.connect()
        now = now_iso()
        count = 0
        with con:
            for s in symbols:
                if not s.get("ins_code"):
                    continue
                con.execute("""
                    INSERT INTO symbols (
                        ins_code, symbol, name,
                        last_price, close_price, yesterday_price,
                        volume, value, trades, eps, pe, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(ins_code) DO UPDATE SET
                        symbol=excluded.symbol,
                        name=excluded.name,
                        last_price=excluded.last_price,
                        close_price=excluded.close_price,
                        yesterday_price=excluded.yesterday_price,
                        volume=excluded.volume,
                        value=excluded.value,
                        trades=excluded.trades,
                        eps=excluded.eps,
                        pe=excluded.pe,
                        updated_at=excluded.updated_at
                """, (
                    s["ins_code"], s.get("symbol", ""), s.get("name", ""),
                    s.get("last_price", 0), s.get("close_price", 0),
                    s.get("yesterday_price", 0), s.get("volume", 0),
                    s.get("value", 0), s.get("trades", 0),
                    s.get("eps", 0), s.get("pe"),
                    now,
                ))
                count += 1
        return count

    def log_fetch(self, source: str, record_count: int, notes: str = ""):
        con = self.conn or self.connect()
        with con:
            con.execute(
                "INSERT INTO fetch_log (source, fetched_at, record_count, notes) VALUES (?, ?, ?, ?)",
                (source, now_iso(), record_count, notes)
            )

    def count_symbols(self) -> int:
        con = self.conn or self.connect()
        return con.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]

    def get_symbol(self, ins_code: str) -> Optional[Dict[str, Any]]:
        con = self.conn or self.connect()
        row = con.execute("SELECT * FROM symbols WHERE ins_code = ?", (ins_code,)).fetchone()
        return dict(row) if row else None

    def list_symbols(self, limit: int = 20) -> List[Dict[str, Any]]:
        con = self.conn or self.connect()
        rows = con.execute(
            "SELECT * FROM symbols ORDER BY trades DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> Dict[str, Any]:
        con = self.conn or self.connect()
        total = con.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
        with_trades = con.execute("SELECT COUNT(*) FROM symbols WHERE trades > 0").fetchone()[0]
        logs = con.execute("SELECT COUNT(*) FROM fetch_log").fetchone()[0]
        return {
            "total_symbols": total,
            "with_trades": with_trades,
            "fetch_logs": logs,
            "db_size_kb": round(self.db_path.stat().st_size / 1024, 1) if self.db_path.exists() else 0,
        }


# --- Test when run directly ---
if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE TEST")
    print("=" * 60)

    # Load normalized symbols
    symbols_path = Path("data/symbols.json")
    if not symbols_path.exists():
        print(f"[ERROR] {symbols_path} not found. Run symbols.py first.")
        raise SystemExit(1)

    with symbols_path.open("r", encoding="utf-8") as f:
        symbols = json.load(f)

    print(f"Loaded {len(symbols)} symbols from {symbols_path}")

    # Init DB
    db = Database()
    db.connect()
    db.init_schema()

    # Upsert
    print("\nUpserting symbols...")
    count = db.upsert_symbols(symbols)
    print(f"Upserted: {count} rows")

    # Log
    db.log_fetch("GetMarketWatch", len(symbols), "Phase 1.1.3 initial load")

    # Stats
    print("\nDatabase stats:")
    for k, v in db.stats().items():
        print(f"  {k}: {v}")

    # Show top 10 by trades
    print("\nTop 10 symbols by trade count:")
    for s in db.list_symbols(limit=10):
        print(f"  {s['symbol']:15s} | {s['name'][:30]:30s} | trades={int(s['trades'])} | last={s['last_price']}")

    # Verify specific symbol
    print("\nVerify FOLAD (46348559193224090):")
    folad = db.get_symbol("46348559193224090")
    if folad:
        print(f"  Found: {folad['symbol']} - {folad['name']}")
        print(f"  Last price: {folad['last_price']}")
        print(f"  Volume: {folad['volume']}")
    else:
        print("  NOT FOUND")

    db.close()
    print("\n" + "=" * 60)
    print("DATABASE TEST COMPLETE")
