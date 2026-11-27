# src/data/incremental.py
# Safe incremental historical data updater.
# Existing database path and schema are preserved.

import sys
import time
import sqlite3
import math
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import requests

from src.config import (
    HEADERS,
    TSETMC_BASE,
    TIMEOUT_DAILY_LIST,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    RETRY_STATUS_CODES,
    STOP_STATUS_CODES,
    DB_PATH,
    DB_TIMEOUT,
)


class IncrementalUpdater:
    """Fetch and safely insert only new historical records."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def close(self):
        self.session.close()

    def _connect(self):
        con = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        return con

    @staticmethod
    def _valid_date(value):
        """Accept valid YYYYMMDD dates only."""
        try:
            text = str(value).strip()
            if len(text) != 8 or not text.isdigit():
                return 0
            datetime.strptime(text, "%Y%m%d")
            return int(text)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_number(value, default=0.0):
        try:
            if value is None or value == "":
                return default
            number = float(value)
            if not math.isfinite(number):
                return default
            return number
        except (TypeError, ValueError, OverflowError):
            return default

    def _get_last_date(self, con, ins_code):
        row = con.execute(
            "SELECT MAX(date) AS d FROM price_history WHERE ins_code = ?",
            (ins_code,),
        ).fetchone()
        return int(row["d"] or 0) if row else 0

    def _fetch_daily_list(self, ins_code):
        url = (
            f"{TSETMC_BASE}/ClosingPrice/"
            f"GetClosingPriceDailyList/{ins_code}/0"
        )

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(
                    url,
                    timeout=TIMEOUT_DAILY_LIST,
                )

                if response.status_code in STOP_STATUS_CODES:
                    print(
                        f"  [STOP] HTTP {response.status_code} - "
                        "access blocked; aborting."
                    )
                    return None

                if (
                    response.status_code in RETRY_STATUS_CODES
                    and attempt < MAX_RETRIES
                ):
                    wait = RETRY_BACKOFF_BASE ** attempt
                    print(
                        f"  [RETRY {attempt}] HTTP "
                        f"{response.status_code} - waiting {wait}s"
                    )
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                data = response.json()

                if not isinstance(data, dict):
                    print("  [ERROR] Invalid API response type")
                    return None

                records = data.get("closingPriceDaily", [])
                return records if isinstance(records, list) else None

            except requests.exceptions.Timeout:
                print(f"  [RETRY {attempt}] Timeout")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_BASE ** attempt)

            except requests.exceptions.ConnectionError:
                print("  [ERROR] Connection failed")
                return None

            except requests.exceptions.HTTPError as exc:
                print(f"  [HTTP ERROR] {exc}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_BASE ** attempt)

            except (ValueError, TypeError) as exc:
                print(f"  [DATA ERROR] {exc}")
                return None

            except Exception as exc:
                print(f"  [ERROR] {type(exc).__name__}: {exc}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_BASE ** attempt)

        return None

    @classmethod
    def _normalize(cls, raw):
        """Normalize and validate one TSETMC history record."""
        if not isinstance(raw, dict):
            return None

        date = cls._valid_date(raw.get("dEven"))
        if not date:
            return None

        record = {
            "date": date,
            "price_close": cls._safe_number(raw.get("pClosing")),
            "price_last": cls._safe_number(raw.get("pDrCotVal")),
            "price_min": cls._safe_number(raw.get("priceMin")),
            "price_max": cls._safe_number(raw.get("priceMax")),
            "price_first": cls._safe_number(raw.get("priceFirst")),
            "price_yesterday": cls._safe_number(
                raw.get("priceYesterday")
            ),
            "price_change": cls._safe_number(raw.get("priceChange")),
            "volume": cls._safe_number(raw.get("qTotTran5J")),
            "value": cls._safe_number(raw.get("qTotCap")),
            "trades": cls._safe_number(raw.get("zTotTran")),
        }

        # Invalid negative price/volume values are rejected.
        nonnegative_fields = (
            "price_close",
            "price_last",
            "price_min",
            "price_max",
            "price_first",
            "price_yesterday",
            "volume",
            "value",
            "trades",
        )

        if any(record[key] < 0 for key in nonnegative_fields):
            return None

        # At least one usable market price must exist.
        if record["price_close"] <= 0 and record["price_last"] <= 0:
            return None

        if record["price_close"] <= 0:
            record["price_close"] = record["price_last"]

        if record["price_last"] <= 0:
            record["price_last"] = record["price_close"]

        return record

    def update_symbol(self, ins_code, symbol_name=""):
        """Update one symbol and return an accurate result."""
        if not ins_code or not str(ins_code).strip():
            return {
                "ins_code": ins_code,
                "status": "INVALID_SYMBOL",
                "added": 0,
            }

        ins_code = str(ins_code).strip()
        print(f"\n[{ins_code}] {symbol_name}")

        con = self._connect()

        try:
            last_date = self._get_last_date(con, ins_code)
            print(f"  Last date in DB: {last_date or 'NONE'}")

            raw_records = self._fetch_daily_list(ins_code)

            if raw_records is None:
                return {
                    "ins_code": ins_code,
                    "status": "FETCH_FAILED",
                    "added": 0,
                }

            if not raw_records:
                return {
                    "ins_code": ins_code,
                    "status": "EMPTY",
                    "added": 0,
                }

            # Normalize, validate, filter dates and remove duplicates
            # within the downloaded response.
            unique_records = {}

            for raw in raw_records:
                record = self._normalize(raw)
                if record is None:
                    continue

                if record["date"] <= last_date:
                    continue

                unique_records[record["date"]] = record

            normalized = sorted(
                unique_records.values(),
                key=lambda record: record["date"],
            )

            if not normalized:
                print("  Already up to date or no valid records.")
                return {
                    "ins_code": ins_code,
                    "status": "UP_TO_DATE",
                    "added": 0,
                }

            print(
                f"  Valid new records: {len(normalized)} "
                f"(from {normalized[0]['date']} "
                f"to {normalized[-1]['date']})"
            )

            from datetime import timezone

            now = datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            )

            added = 0

            # Transaction: all valid inserts commit together.
            with con:
                for record in normalized:
                    cursor = con.execute(
                        """
                        INSERT INTO price_history (
                            ins_code, date, price_close, price_last,
                            price_min, price_max, price_first,
                            price_yesterday, price_change,
                            volume, value, trades, source, inserted_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(ins_code, date) DO NOTHING
                        """,
                        (
                            ins_code,
                            record["date"],
                            record["price_close"],
                            record["price_last"],
                            record["price_min"],
                            record["price_max"],
                            record["price_first"],
                            record["price_yesterday"],
                            record["price_change"],
                            record["volume"],
                            record["value"],
                            record["trades"],
                            "incremental",
                            now,
                        ),
                    )

                    # Count only rows actually inserted.
                    if cursor.rowcount == 1:
                        added += 1

            print(f"  Actually added: {added} rows")

            return {
                "ins_code": ins_code,
                "status": "UPDATED" if added else "UP_TO_DATE",
                "added": added,
            }

        finally:
            con.close()


if __name__ == "__main__":
    ins_code = "46348559193224090"
    symbol = "FOLAD (فولاد)"

    updater = IncrementalUpdater()

    try:
        print("=" * 60)
        print("INCREMENTAL UPDATE")
        print("=" * 60)

        result = updater.update_symbol(ins_code, symbol)

        print()
        print("=" * 60)
        print(
            f"RESULT: {result['status']} | "
            f"added={result['added']}"
        )
        print("=" * 60)

    finally:
        updater.close()
