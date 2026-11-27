import unittest

from src.data.history import extract_history_record
from src.data.incremental import IncrementalUpdater
from src.data.batch_downloader import _normalize_batch_record


def base_record():
    return {
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


BATCH_KEYS = [
    "date",
    "price_close",
    "price_last",
    "price_min",
    "price_max",
    "price_first",
    "price_yesterday",
    "price_change",
    "volume",
    "value",
    "trades",
]


def batch_to_dict(result):
    if result is None:
        return None
    return dict(zip(BATCH_KEYS, result))


class TestCrossModuleValidationContracts(unittest.TestCase):

    def test_valid_record_core_fields_match(self):
        raw = base_record()

        history = extract_history_record(raw)
        incremental = IncrementalUpdater._normalize(raw)
        batch = batch_to_dict(_normalize_batch_record(raw))

        self.assertIsNotNone(history)
        self.assertIsNotNone(incremental)
        self.assertIsNotNone(batch)

        for key in BATCH_KEYS:
            with self.subTest(field=key):
                self.assertEqual(history[key], incremental[key])
                self.assertEqual(history[key], batch[key])

    def test_invalid_date_rejected_by_all(self):
        raw = base_record()
        raw["dEven"] = "20240230"

        self.assertIsNone(extract_history_record(raw))
        self.assertIsNone(IncrementalUpdater._normalize(raw))
        self.assertIsNone(_normalize_batch_record(raw))

    def test_both_main_prices_zero_rejected_by_all(self):
        raw = base_record()
        raw["pClosing"] = 0
        raw["pDrCotVal"] = 0

        self.assertIsNone(extract_history_record(raw))
        self.assertIsNone(IncrementalUpdater._normalize(raw))
        self.assertIsNone(_normalize_batch_record(raw))

    def test_price_fallback_consistent(self):
        raw = base_record()
        raw["pClosing"] = 0
        raw["pDrCotVal"] = 15000

        for result in (
            extract_history_record(raw),
            IncrementalUpdater._normalize(raw),
            batch_to_dict(_normalize_batch_record(raw)),
        ):
            self.assertIsNotNone(result)
            self.assertEqual(result["price_close"], 15000)
            self.assertEqual(result["price_last"], 15000)

        raw = base_record()
        raw["pClosing"] = 15000
        raw["pDrCotVal"] = 0

        for result in (
            extract_history_record(raw),
            IncrementalUpdater._normalize(raw),
            batch_to_dict(_normalize_batch_record(raw)),
        ):
            self.assertIsNotNone(result)
            self.assertEqual(result["price_close"], 15000)
            self.assertEqual(result["price_last"], 15000)

    def test_negative_price_change_allowed_by_all(self):
        raw = base_record()
        raw["priceChange"] = -500

        for result in (
            extract_history_record(raw),
            IncrementalUpdater._normalize(raw),
            batch_to_dict(_normalize_batch_record(raw)),
        ):
            self.assertIsNotNone(result)
            self.assertEqual(result["price_change"], -500)

    def test_negative_non_change_fields_current_divergence(self):
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
                raw = base_record()
                raw[field] = -1

                self.assertIsNotNone(extract_history_record(raw))
                self.assertIsNone(IncrementalUpdater._normalize(raw))
                self.assertIsNone(_normalize_batch_record(raw))

    def test_non_finite_secondary_fields_current_divergence(self):
        raw = base_record()
        raw["priceMin"] = float("nan")
        raw["priceMax"] = float("inf")
        raw["qTotTran5J"] = float("-inf")

        history = extract_history_record(raw)
        incremental = IncrementalUpdater._normalize(raw)
        batch = _normalize_batch_record(raw)

        self.assertIsNotNone(history)
        self.assertIsNotNone(incremental)
        self.assertIsNone(batch)

        self.assertEqual(history["price_min"], 0)
        self.assertEqual(history["price_max"], 0)
        self.assertEqual(history["volume"], 0)

        self.assertEqual(incremental["price_min"], 0)
        self.assertEqual(incremental["price_max"], 0)
        self.assertEqual(incremental["volume"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
