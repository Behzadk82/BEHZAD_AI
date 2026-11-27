#!/usr/bin/env python3

"""
BEHZAD_AI - Historical Data Engine Tests

Offline tests.
No network requests.
No database access.
No existing project data is modified.
"""

import sys
import json
import unittest
import tempfile

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.history import HistoryFetcher


class TestHistoryEngine(unittest.TestCase):

    def setUp(self):

        self.fetcher = HistoryFetcher(
            retries=1,
            retry_delay=0
        )

    def tearDown(self):

        self.fetcher.close()

    # -----------------------------------------------
    # Safe conversion
    # -----------------------------------------------

    def test_safe_float(self):

        self.assertEqual(
            HistoryFetcher.safe_float("123.45"),
            123.45
        )

        self.assertEqual(
            HistoryFetcher.safe_float(None),
            0.0
        )

        self.assertEqual(
            HistoryFetcher.safe_float("invalid"),
            0.0
        )

        self.assertEqual(
            HistoryFetcher.safe_float(""),
            0.0
        )

    def test_safe_int(self):

        self.assertEqual(
            HistoryFetcher.safe_int("100"),
            100
        )

        self.assertEqual(
            HistoryFetcher.safe_int(None),
            0
        )

        self.assertEqual(
            HistoryFetcher.safe_int("invalid"),
            0
        )

    # -----------------------------------------------
    # Date validation
    # -----------------------------------------------

    def test_valid_dates(self):

        self.assertTrue(
            HistoryFetcher.is_valid_date(20250115)
        )

        self.assertTrue(
            HistoryFetcher.is_valid_date(20240229)
        )

    def test_invalid_dates(self):

        self.assertFalse(
            HistoryFetcher.is_valid_date(20250229)
        )

        self.assertFalse(
            HistoryFetcher.is_valid_date(20251301)
        )

        self.assertFalse(
            HistoryFetcher.is_valid_date(2025011)
        )

        self.assertFalse(
            HistoryFetcher.is_valid_date(0)
        )

    # -----------------------------------------------
    # Normalization
    # -----------------------------------------------

    def test_normalize_sort_and_duplicates(self):

        sample = [
            {
                "dEven": 20250103,
                "pClosing": 300,
                "pDrCotVal": 301,
            },
            {
                "dEven": 20250101,
                "pClosing": 100,
                "pDrCotVal": 101,
            },
            {
                "dEven": 20250101,
                "pClosing": 999,
                "pDrCotVal": 999,
            },
            {
                "dEven": 20250102,
                "pClosing": 200,
                "pDrCotVal": 201,
            },
        ]

        result = HistoryFetcher.normalize_history(
            sample
        )

        self.assertEqual(len(result), 3)

        dates = [
            record["date"]
            for record in result
        ]

        self.assertEqual(
            dates,
            [20250101, 20250102, 20250103]
        )

    def test_invalid_price_removed(self):

        sample = [
            {
                "dEven": 20250101,
                "pClosing": 0,
                "pDrCotVal": 0,
            },
            {
                "dEven": 20250102,
                "pClosing": -5,
                "pDrCotVal": -1,
            },
            {
                "dEven": 20250103,
                "pClosing": 100,
                "pDrCotVal": 101,
            },
        ]

        result = HistoryFetcher.normalize_history(
            sample
        )

        self.assertEqual(len(result), 1)

        self.assertEqual(
            result[0]["date"],
            20250103
        )

    def test_missing_close_fallback(self):

        sample = [
            {
                "dEven": 20250101,
                "pClosing": 0,
                "pDrCotVal": 125,
            }
        ]

        result = HistoryFetcher.normalize_history(
            sample
        )

        self.assertEqual(len(result), 1)

        self.assertEqual(
            result[0]["price_close"],
            125
        )

        self.assertEqual(
            result[0]["price_last"],
            125
        )

    def test_invalid_date_removed(self):

        sample = [
            {
                "dEven": 20251301,
                "pClosing": 100,
                "pDrCotVal": 100,
            },
            {
                "dEven": 20250101,
                "pClosing": 100,
                "pDrCotVal": 100,
            },
        ]

        result = HistoryFetcher.normalize_history(
            sample
        )

        self.assertEqual(len(result), 1)

        self.assertEqual(
            result[0]["date"],
            20250101
        )

    # -----------------------------------------------
    # Statistics
    # -----------------------------------------------

    def test_statistics(self):

        records = [
            {
                "date": 20250101,
                "volume": 100,
                "value": 1000,
                "trades": 10,
            },
            {
                "date": 20250102,
                "volume": 200,
                "value": 3000,
                "trades": 20,
            },
        ]

        stats = HistoryFetcher.history_statistics(
            records
        )

        self.assertEqual(
            stats["count"],
            2
        )

        self.assertEqual(
            stats["oldest_date"],
            20250101
        )

        self.assertEqual(
            stats["latest_date"],
            20250102
        )

        self.assertEqual(
            stats["total_volume"],
            300
        )

        self.assertEqual(
            stats["total_value"],
            4000
        )

        self.assertEqual(
            stats["total_trades"],
            30
        )

    # -----------------------------------------------
    # JSON saving
    # -----------------------------------------------

    def test_save_json(self):

        payload = {
            "symbol": "فولاد",
            "price": 12345,
        }

        with tempfile.TemporaryDirectory() as tmp:

            target = Path(tmp) / "test.json"

            success = HistoryFetcher.save_json(
                payload,
                str(target)
            )

            self.assertTrue(success)
            self.assertTrue(target.exists())

            with target.open(
                "r",
                encoding="utf-8"
            ) as file:

                loaded = json.load(file)

            self.assertEqual(
                loaded["symbol"],
                "فولاد"
            )

            self.assertEqual(
                loaded["price"],
                12345
            )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )
