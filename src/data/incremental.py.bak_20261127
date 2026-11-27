# src/data/incremental.py
# Incremental update: fetch only new days, not full history.
# Uses config.py for timeouts, retries, delays.

import sys
import time
import sqlite3
from pathlib import Path

# Add project root to path so we can import config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import requests
from src.config import (
    HEADERS, TSETMC_BASE,
    TIMEOUT_DAILY_LIST,
    MAX_RETRIES, RETRY_BACKOFF_BASE,
    RETRY_STATUS_CODES, STOP_STATUS_CODES,
    DELAY_BEFORE_RETRY,
    DB_PATH, DB_TIMEOUT,
)


class IncrementalUpdater:
    """Fetch only new days for a symbol."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # ---------- DB helpers ----------
    def _connect(self):
        con = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        return con

    def _get_last_date(self, con, ins_code: str) -> int:
        """Return the latest date in DB for this symbol, or 0 if none."""
        row = con.execute(
            "SELECT MAX(date) AS d FROM price_history WHERE ins_code = ?",
            (ins_code,)
        ).fetchone()
        return row["d"] if row and row["d"] else 0

    # ---------- API ----------
    def _fetch_daily_list(self, ins_code: str) -> list | None:
        """Fetch full daily history with retry."""
        url = f"{TSETMC_BASE}/ClosingPrice/GetClosingPriceDailyList/{ins_code}/0"
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = self.session.get(url, timeout=TIMEOUT_DAILY_LIST)
                if r.status_code in STOP_STATUS_CODES:
                    print(f"  [STOP] HTTP {r.status_code} - blocking. Aborting.")
                    return None
                if r.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    print(f"  [RETRY {attempt}] HTTP {r.status_code} - waiting {wait}s")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                data = r.json()
                records = data.get("closingPriceDaily", [])
                return records if isinstance(records, list) else None
            except requests.exceptions.Timeout:
                print(f"  [RETRY {attempt}] Timeout")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_BASE ** attempt)
            except requests.exceptions.ConnectionError:
                print(f"  [ERROR] Connection failed - check VPN")
                return None
            except Exception as e:
                print(f"  [ERROR] {type(e).__name__}: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_BASE ** attempt)
        return None

    @staticmethod
    def _normalize(raw: dict) -> dict:
        return {
            "date": int(raw.get("dEven", 0)),
            "price_close": float(raw.get("pClosing", 0) or 0),
            "price_last": float(raw.get("pDrCotVal", 0) or 0),
            "price_min": float(raw.get("priceMin", 0) or 0),
            "price_max": float(raw.get("priceMax", 0) or 0),
            "price_first": float(raw.get("priceFirst", 0) or 0),
            "price_yesterday": float(raw.get("priceYesterday", 0) or 0),
            "price_change": float(raw.get("priceChange", 0) or 0),
            "volume": float(raw.get("qTotTran5J", 0) or 0),
            "value": float(raw.get("qTotCap", 0) or 0),
            "trades": float(raw.get("zTotTran", 0) or 0),
        }

    # ---------- Main update ----------
    def update_symbol(self, ins_code: str, symbol_name: str = "") -> dict:
        """Update one symbol. Returns status dict."""
        print(f"\n[{ins_code}] {symbol_name}")

        con = self._connect()
        try:
            last_date = self._get_last_date(con, ins_code)
            print(f"  Last date in DB: {last_date if last_date else 'NONE'}")

            raw_records = self._fetch_daily_list(ins_code)
            if raw_records is None:
                return {"ins_code": ins_code, "status": "FETCH_FAILED", "added": 0}
            if not raw_records:
                return {"ins_code": ins_code, "status": "EMPTY", "added": 0}

            normalized = [self._normalize(r) for r in raw_records]
            normalized = [r for r in normalized if r["date"] > last_date]

            if not normalized:
                print(f"  Already up to date.")
                return {"ins_code": ins_code, "status": "UP_TO_DATE", "added": 0}

            normalized.sort(key=lambda r: r["date"])
            print(f"  New records: {len(normalized)} (from {normalized[0]['date']} to {normalized[-1]['date']})")

            # Insert
            now = "2026-11-25T00:00:00+00:00"  # we'll use a simple ISO
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")

            added = 0
            with con:
                for r in normalized:
                    con.execute("""
                        INSERT INTO price_history (
                            ins_code, date, price_close, price_last,
                            price_min, price_max, price_first,
                            price_yesterday, price_change,
                            volume, value, trades, source, inserted_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(ins_code, date) DO NOTHING
                    """, (
                        ins_code, r["date"], r["price_close"], r["price_last"],
                        r["price_min"], r["price_max"], r["price_first"],
                        r["price_yesterday"], r["price_change"],
                        r["volume"], r["value"], r["trades"],
                        "incremental", now,
                    ))
                    added += 1

            print(f"  Added: {added} rows")
            return {"ins_code": ins_code, "status": "UPDATED", "added": added}
        finally:
            con.close()


if __name__ == "__main__":
    ins_code = "46348559193224090"
    symbol = "FOLAD (فولاد)"

    updater = IncrementalUpdater()
    print("=" * 60)
    print("INCREMENTAL UPDATE")
    print("=" * 60)

    result = updater.update_symbol(ins_code, symbol)

    print()
    print("=" * 60)
    print(f"RESULT: {result['status']} | added={result['added']}")
    print("=" * 60)
