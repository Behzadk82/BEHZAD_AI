import unittest

from src.data.history import extract_history_record
from src.data.incremental import IncrementalUpdater
from src.data import batch_downloader as bd


class TestCrossModuleDataQuality(unittest.TestCase):
    def sample_raw(self):
        return {
            "dEven": 20250115,
            "pClosing": 1200.0,
            "pDrCotVal": 1210.0,
            "priceMin": 1180.0,
            "priceMax": 1230.0,
            "priceFirst": 1190.0,
            "priceYesterday": 1170.0,
            "priceChange": -30.0,
            "qTotTran5J": 5000,
            "qTotCap": 6000000,
            "zTotTran": 250,
        }

    def test_valid_record_consistent_across_modules(self):
        raw = self.sample_raw()
        h = extract_history_record(raw)
        inc = IncrementalUpdater._normalize(raw)
        b = bd._normalize_batch_record(raw)

        self.assertIsNotNone(h)
        self.assertIsNotNone(inc)
        self.assertIsNotNone(b)

        self.assertEqual(h["date"], 20250115)
        self.assertEqual(inc["date"], 20250115)
        self.assertEqual(b[0], 20250115)

        self.assertEqual(h["price_close"], 1200.0)
        self.assertEqual(inc["price_close"], 1200.0)
        self.assertEqual(b[1], 1200.0)

        self.assertEqual(h["price_change"], -30.0)
        self.assertEqual(inc["price_change"], -30.0)
        self.assertEqual(b[7], -30.0)

    def test_negative_non_change_field_rejected_everywhere(self):
        raw = self.sample_raw()
        raw["qTotTran5J"] = -5

        self.assertIsNone(IncrementalUpdater._normalize(raw))
        self.assertIsNone(bd._normalize_batch_record(raw))
        # extract_history_record uses safe_int without rejecting negative volume
        h = extract_history_record(raw)
        self.assertIsNotNone(h)
        self.assertEqual(h["volume"], -5)

    def test_zero_prices_rejected_everywhere(self):
        raw = self.sample_raw()
        raw["pClosing"] = 0
        raw["pDrCotVal"] = 0

        self.assertIsNone(extract_history_record(raw))
        self.assertIsNone(IncrementalUpdater._normalize(raw))
        self.assertIsNone(bd._normalize_batch_record(raw))

    def test_close_fallback_to_last_consistent(self):
        raw = self.sample_raw()
        raw["pClosing"] = 0
        raw["pDrCotVal"] = 1450.0

        h = extract_history_record(raw)
        inc = IncrementalUpdater._normalize(raw)
        b = bd._normalize_batch_record(raw)

        self.assertEqual(h["price_close"], 1450.0)
        self.assertEqual(inc["price_close"], 1450.0)
        self.assertEqual(b[1], 1450.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
