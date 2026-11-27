# -*- coding: utf-8 -*-
"""BEHZAD_AI historical market data engine."""

from __future__ import annotations

import json
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


BASE_URL = (
    "https://cdn.tsetmc.com/api/ClosingPrice/"
    "GetClosingPriceDailyList"
)


def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        result = float(value)
        if not math.isfinite(result):
            return default
        return result
    except (TypeError, ValueError, OverflowError):
        return default


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return default


def safe_json(data, default=None):
    if default is None:
        default = {}

    if isinstance(data, (dict, list)):
        return data

    if not isinstance(data, str):
        return default

    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError, ValueError):
        return default


def normalize_date(value):
    """Validate date strictly and return YYYYMMDD integer."""
    if value is None or isinstance(value, bool):
        return None

    text = str(value).strip()

    # Numeric date must be exactly 8 digits.
    if text.isdigit():
        if len(text) != 8:
            return None
        fmt = "%Y%m%d"
    elif len(text) == 10 and "-" in text:
        fmt = "%Y-%m-%d"
    elif len(text) == 10 and "/" in text:
        fmt = "%Y/%m/%d"
    elif len(text) == 19:
        fmt = "%Y-%m-%d %H:%M:%S"
    else:
        return None

    try:
        parsed = datetime.strptime(text, fmt)
        return int(parsed.strftime("%Y%m%d"))
    except (ValueError, TypeError):
        return None


def is_valid_date(value):
    return normalize_date(value) is not None


def extract_history_record(record):
    if not isinstance(record, dict):
        return None

    date_value = normalize_date(
        record.get("dEven", record.get("date"))
    )

    if date_value is None:
        return None

    close = safe_float(
        record.get("pClosing", record.get("price_close"))
    )
    last = safe_float(
        record.get("pDrCotVal", record.get("price_last"))
    )

    # Use last price as closing fallback if close is invalid.
    if close <= 0 and last > 0:
        close = last

    # Reject records when neither price is valid.
    if close <= 0 and last <= 0:
        return None

    if last <= 0 and close > 0:
        last = close

    item = {
        "date": date_value,
        "price_close": close,
        "price_last": last,
        "price_open": safe_float(
            record.get("priceFirst", record.get("price_open"))
        ),
        "price_high": safe_float(
            record.get("priceMax", record.get("price_high"))
        ),
        "price_low": safe_float(
            record.get("priceMin", record.get("price_low"))
        ),
        "price_yesterday": safe_float(
            record.get("priceYesterday", record.get("price_yesterday"))
        ),
        "price_change": safe_float(
            record.get("priceChange", record.get("price_change"))
        ),
        "volume": safe_int(record.get("qTotTran5J", record.get("volume"))),
        "value": safe_int(record.get("qTotCap", record.get("value"))),
        "trades": safe_int(record.get("zTotTran", record.get("trades"))),
    }

    # Legacy aliases for compatibility with other project modules.
    item.update({
        "close": item["price_close"],
        "last": item["price_last"],
        "open": item["price_open"],
        "high": item["price_high"],
        "low": item["price_low"],
        "yesterday": item["price_yesterday"],
        "change": item["price_change"],
    })

    return item


def normalize_history(records):
    if not isinstance(records, list):
        return []

    by_date = {}

    for record in records:
        item = extract_history_record(record)
        if item is not None:
            # Last occurrence of a duplicate date wins.
            by_date[item["date"]] = item

    return sorted(by_date.values(), key=lambda item: item["date"])


def history_statistics(records):
    if not isinstance(records, list):
        records = []

    valid = []

    for record in records:
        if not isinstance(record, dict):
            continue

        date_value = normalize_date(record.get("date", record.get("dEven")))
        if date_value is None:
            continue

        valid.append({
            "date": date_value,
            "volume": safe_int(record.get("volume", record.get("qTotTran5J"))),
            "value": safe_int(record.get("value", record.get("qTotCap"))),
            "trades": safe_int(record.get("trades", record.get("zTotTran"))),
            "close": safe_float(
                record.get("price_close", record.get("close", record.get("pClosing")))
            ),
        })

    valid.sort(key=lambda item: item["date"])

    if not valid:
        return {
            "count": 0,
            "oldest_date": None,
            "latest_date": None,
            "first_date": None,
            "last_date": None,
            "min_price": None,
            "max_price": None,
            "average_close": None,
            "total_volume": 0,
            "total_value": 0,
            "total_trades": 0,
        }

    prices = [item["close"] for item in valid if item["close"] > 0]

    oldest = valid[0]["date"]
    latest = valid[-1]["date"]

    return {
        "count": len(valid),
        "oldest_date": oldest,
        "latest_date": latest,
        "first_date": oldest,
        "last_date": latest,
        "min_price": min(prices) if prices else None,
        "max_price": max(prices) if prices else None,
        "average_close": sum(prices) / len(prices) if prices else None,
        "total_volume": sum(item["volume"] for item in valid),
        "total_value": sum(item["value"] for item in valid),
        "total_trades": sum(item["trades"] for item in valid),
    }


class HistoryFetcher:
    BASE_URL = BASE_URL

    def __init__(self, timeout=40, retries=3, retry_delay=2):
        self.timeout = timeout
        self.retries = max(1, safe_int(retries, 3))
        self.retry_delay = max(0.0, safe_float(retry_delay, 2.0))

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 10) "
                "AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://cdn.tsetmc.com/",
        })

    @staticmethod
    def safe_float(value, default=0.0):
        return safe_float(value, default)

    @staticmethod
    def safe_int(value, default=0):
        return safe_int(value, default)

    @staticmethod
    def safe_json(data, default=None):
        return safe_json(data, default)

    @staticmethod
    def is_valid_date(value):
        return is_valid_date(value)

    @staticmethod
    def normalize_date(value):
        return normalize_date(value)

    @staticmethod
    def extract_history_record(record):
        return extract_history_record(record)

    @staticmethod
    def normalize_history(records):
        return normalize_history(records)

    @staticmethod
    def history_statistics(records):
        return history_statistics(records)

    @staticmethod
    def save_json(data, filepath):
        """Save JSON safely with UTF-8, preserving Persian text."""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            with path.open("w", encoding="utf-8") as file:
                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=2,
                    allow_nan=False,
                )

            return True
        except (OSError, TypeError, ValueError):
            return False

    def get_history(self, ins_code):
        if not ins_code:
            return None

        url = f"{self.BASE_URL}/{ins_code}/0"

        for attempt in range(self.retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()

                if not isinstance(payload, dict):
                    return None

                records = payload.get("closingPriceDaily", [])
                if not isinstance(records, list):
                    return None

                return normalize_history(records)

            except requests.exceptions.RequestException:
                if attempt + 1 < self.retries:
                    time.sleep(self.retry_delay)

            except (ValueError, TypeError):
                if attempt + 1 < self.retries:
                    time.sleep(self.retry_delay)

        return None

    def fetch_and_save(self, ins_code, save_callback=None):
        records = self.get_history(ins_code)

        if records is None:
            return None

        if callable(save_callback):
            save_callback(ins_code, records)

        return records

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False


if __name__ == "__main__":
    import sys

    code = (
        sys.argv[1]
        if len(sys.argv) > 1
        else input("Enter TSETMC instrument code: ").strip()
    )

    with HistoryFetcher() as fetcher:
        data = fetcher.get_history(code)

    if data is None:
        print("FAILED: Could not fetch historical data.")
    else:
        print("SUCCESS: Records =", len(data))
        if data:
            print("First record:", data[0])
            print("Last record:", data[-1])
            print("Statistics:", history_statistics(data))
