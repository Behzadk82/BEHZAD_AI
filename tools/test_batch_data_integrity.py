import unittest

from src.data.batch_downloader import (
    _normalize_batch_record,
    _count_valid_history_records,
)


def valid_record(**overrides):
    record = {
        "dEven": 14030101,
        "pClosing": 100,
        "pDrCotVal": 105,
        "priceMin": 95,
        "priceMax": 110,
        "priceFirst": 98,
        "priceYesterday": 99,
        "priceChange": 6,
        "qTotTran5J": 1000,
        "qTotCap": 50000,
        "zTotTran": 20,
    }
    record.update(overrides)
    return record


class BatchDataIntegrityTests(unittest.TestCase):

    def test_valid_record(self):
        self.assertIsNotNone(_normalize_batch_record(valid_record()))

    def test_valid_existing_sample_date(self):
        self.assertIsNotNone(
            _normalize_batch_record(valid_record(dEven=14030101))
        )

    def test_invalid_gregorian_date(self):
        self.assertIsNone(
            _normalize_batch_record(valid_record(dEven=20250229))
        )

    def test_invalid_date_format(self):
        self.assertIsNone(
            _normalize_batch_record(valid_record(dEven=2025011))
        )

    def test_negative_price_rejected(self):
        self.assertIsNone(
            _normalize_batch_record(valid_record(pClosing=-1))
        )

    def test_negative_volume_rejected(self):
        self.assertIsNone(
            _normalize_batch_record(valid_record(qTotTran5J=-1))
        )

    def test_negative_price_change_allowed(self):
        result = _normalize_batch_record(
            valid_record(priceChange=-5)
        )
        self.assertIsNotNone(result)
        self.assertEqual(result[7], -5)

    def test_both_prices_zero_rejected(self):
        self.assertIsNone(
            _normalize_batch_record(
                valid_record(pClosing=0, pDrCotVal=0)
            )
        )

    def test_close_fallback_from_last(self):
        result = _normalize_batch_record(
            valid_record(pClosing=0, pDrCotVal=105)
        )
        self.assertIsNotNone(result)
        self.assertEqual(result[1], 105)
        self.assertEqual(result[2], 105)

    def test_last_fallback_from_close(self):
        result = _normalize_batch_record(
            valid_record(pClosing=100, pDrCotVal=0)
        )
        self.assertIsNotNone(result)
        self.assertEqual(result[1], 100)
        self.assertEqual(result[2], 100)

    def test_nan_rejected(self):
        self.assertIsNone(
            _normalize_batch_record(valid_record(pClosing=float("nan")))
        )

    def test_infinity_rejected(self):
        self.assertIsNone(
            _normalize_batch_record(valid_record(pClosing=float("inf")))
        )

    def test_non_dict_rejected(self):
        self.assertIsNone(_normalize_batch_record(None))

    def test_count_uses_same_validation(self):
        records = [
            valid_record(),
            valid_record(pClosing=-1),
            valid_record(priceChange=-3),
            valid_record(dEven=20250229),
            valid_record(pClosing=0, pDrCotVal=110),
        ]

        expected = sum(
            _normalize_batch_record(record) is not None
            for record in records
        )

        self.assertEqual(
            _count_valid_history_records(records),
            expected,
        )

    def test_duplicates_count_as_valid_records(self):
        records = [valid_record(), valid_record()]
        self.assertEqual(
            _count_valid_history_records(records),
            2,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
