# -*- coding: utf-8 -*-
"""Isolated tests for IncrementalUpdater normalization."""

import math
import unittest

from src.data.incremental import IncrementalUpdater


class TestIncrementalNormalization(unittest.TestCase):

    def setUp(self):
        self.valid_record = {
            "dEven": 14030115,
            "pClosing": 12500,
            "pDrCotVal": 12600,
            "priceMin": 12000,
            "priceMax": 13000,
            "priceFirst": 12200,
            "priceYesterday": 12400,
            "priceChange": -200,
            "qTotTran5J": 150000,
            "qTotCap": 1800000000,
            "zTotTran": 250,
        }

    def normalize(self, raw="__DEFAULT_RECORD__"):
        if raw == "__DEFAULT_RECORD__":
            raw = self.valid_record.copy()
        return IncrementalUpdater._normalize(raw)

    def test_valid_record(self):
        result = self.normalize()

        self.assertIsNotNone(result)
        self.assertEqual(result["date"], 14030115)
        self.assertEqual(result["price_close"], 12500)
        self.assertEqual(result["price_last"], 12600)

    def test_non_dict_rejected(self):
        self.assertIsNone(self.normalize([]))
        self.assertIsNone(self.normalize("invalid"))
        self.assertIsNone(self.normalize(None))

    def test_invalid_dates_rejected(self):
        invalid_dates = [
            None,
            "",
            "2024-01-15",
            "14030230",
            "1234567",
            "abcdefgh",
        ]

        for date in invalid_dates:
            with self.subTest(date=date):
                raw = self.valid_record.copy()
                raw["dEven"] = date
                self.assertIsNone(self.normalize(raw))

    def test_negative_fields_rejected(self):
        fields = [
            "pClosing",
            "pDrCotVal",
            "priceMin",
            "priceMax",
            "priceFirst",
            "priceYesterday",
            "qTotTran5J",
            "qTotCap",
            "zTotTran",
        ]

        for field in fields:
            with self.subTest(field=field):
                raw = self.valid_record.copy()
                raw[field] = -1
                self.assertIsNone(self.normalize(raw))

    def test_negative_price_change_allowed(self):
        raw = self.valid_record.copy()
        raw["priceChange"] = -500

        result = self.normalize(raw)

        self.assertIsNotNone(result)
        self.assertEqual(result["price_change"], -500)

    def test_both_main_prices_zero_rejected(self):
        raw = self.valid_record.copy()
        raw["pClosing"] = 0
        raw["pDrCotVal"] = 0

        self.assertIsNone(self.normalize(raw))

    def test_close_fallback_from_last(self):
        raw = self.valid_record.copy()
        raw["pClosing"] = 0
        raw["pDrCotVal"] = 15000

        result = self.normalize(raw)

        self.assertIsNotNone(result)
        self.assertEqual(result["price_close"], 15000)
        self.assertEqual(result["price_last"], 15000)

    def test_last_fallback_from_close(self):
        raw = self.valid_record.copy()
        raw["pClosing"] = 15000
        raw["pDrCotVal"] = 0

        result = self.normalize(raw)

        self.assertIsNotNone(result)
        self.assertEqual(result["price_close"], 15000)
        self.assertEqual(result["price_last"], 15000)

    def test_nan_and_infinity_become_zero(self):
        raw = self.valid_record.copy()
        raw["priceMin"] = float("nan")
        raw["priceMax"] = float("inf")
        raw["qTotTran5J"] = float("-inf")

        result = self.normalize(raw)

        self.assertIsNotNone(result)
        self.assertEqual(result["price_min"], 0)
        self.assertEqual(result["price_max"], 0)
        self.assertEqual(result["volume"], 0)

    def test_non_finite_main_prices(self):
        raw = self.valid_record.copy()
        raw["pClosing"] = float("nan")
        raw["pDrCotVal"] = 12600

        result = self.normalize(raw)

        self.assertIsNotNone(result)
        self.assertEqual(result["price_close"], 12600)

    def test_numeric_strings_accepted(self):
        raw = self.valid_record.copy()
        raw["pClosing"] = "12500.5"
        raw["qTotTran5J"] = "150000"

        result = self.normalize(raw)

        self.assertIsNotNone(result)
        self.assertEqual(result["price_close"], 12500.5)
        self.assertEqual(result["volume"], 150000)

    def test_empty_values_become_zero(self):
        raw = self.valid_record.copy()
        raw["priceMin"] = ""
        raw["priceMax"] = None

        result = self.normalize(raw)

        self.assertIsNotNone(result)
        self.assertEqual(result["price_min"], 0)
        self.assertEqual(result["price_max"], 0)

    def test_all_numeric_results_are_finite(self):
        result = self.normalize()

        for key, value in result.items():
            if key != "date":
                with self.subTest(field=key):
                    self.assertTrue(math.isfinite(value))


if __name__ == "__main__":
    unittest.main(verbosity=2)
