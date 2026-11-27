import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.data import batch_downloader as m


SAMPLE_RECORDS = [
    {
        "dEven": 14030101,
        "pClosing": 1000,
        "pDrCotVal": 1000,
        "priceMin": 950,
        "priceMax": 1050,
        "priceFirst": 980,
        "priceYesterday": 990,
        "priceChange": 10,
        "qTotTran5J": 100,
        "qTotCap": 100000,
        "zTotTran": 50,
    }
]


class TestProcessBatchIntegration(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="behzad_process_batch_"
        )
        self.root = Path(self.temp.name)

        self.db_path = self.root / "test.db"
        self.raw_dir = self.root / "raw"
        self.checkpoint_file = self.root / "checkpoint.json"

        self.patches = [
            patch.object(m, "DB_PATH", self.db_path),
            patch.object(m, "RAW_DIR", self.raw_dir),
            patch.object(m, "CHECKPOINT_FILE", self.checkpoint_file),
            patch.object(m, "DELAY_BETWEEN_SYMBOLS", 0),
            patch.object(m.time, "sleep"),
        ]

        for p in self.patches:
            p.start()

        self.state = m.empty_state()

        self.batch = [
            {
                "ins_code": "12345",
                "symbol": "TEST_SYMBOL",
            }
        ]

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()

        self.temp.cleanup()

    def test_success_and_duplicate_retry(self):
        """
        Successful processing and a retry where the DB
        reports zero new rows due to duplicate protection.
        """

        with patch.object(
            m,
            "fetch_with_retry",
            return_value=(SAMPLE_RECORDS, None),
        ), patch.object(
            m,
            "save_to_db",
            side_effect=[2, 0],
        ) as mock_db:

            first = m.process_batch(
                self.batch,
                self.state,
                session=None,
            )

            second = m.process_batch(
                self.batch,
                self.state,
                session=None,
            )

        self.assertEqual(first, (1, 0, False))
        self.assertEqual(second, (1, 0, False))

        self.assertEqual(mock_db.call_count, 2)

        self.assertIn(
            "12345",
            self.state["completed"],
        )

        self.assertTrue(
            (self.raw_dir / "12345.json").exists()
        )

        self.assertTrue(self.checkpoint_file.exists())

        with self.checkpoint_file.open(
            encoding="utf-8"
        ) as f:
            checkpoint = json.load(f)

        self.assertIn(
            "12345",
            checkpoint["completed"],
        )

        self.assertEqual(
            len(checkpoint["completed"]),
            1,
        )

    def test_sensitive_http_stop(self):
        """
        Sensitive HTTP errors must stop processing,
        mark the symbol as failed and save checkpoint.
        """

        with patch.object(
            m,
            "fetch_with_retry",
            return_value=(None, "STOP_403"),
        ):

            result = m.process_batch(
                self.batch,
                self.state,
                session=None,
            )

        self.assertEqual(result, (0, 0, True))

        self.assertNotIn(
            "12345",
            self.state["completed"],
        )

        self.assertTrue(
            self.checkpoint_file.exists()
        )

        with self.checkpoint_file.open(
            encoding="utf-8"
        ) as f:
            checkpoint = json.load(f)

        self.assertNotIn(
            "12345",
            checkpoint["completed"],
        )

    def test_invalid_history_is_not_completed(self):
        """
        Invalid history data must not be marked completed.
        """

        invalid_records = [
            {"dEven": 0, "pClosing": "invalid"}
        ]

        with patch.object(
            m,
            "fetch_with_retry",
            return_value=(invalid_records, None),
        ), patch.object(
            m,
            "save_to_db",
        ) as mock_db:

            result = m.process_batch(
                self.batch,
                self.state,
                session=None,
            )

        self.assertEqual(result, (0, 1, False))

        mock_db.assert_not_called()

        self.assertNotIn(
            "12345",
            self.state["completed"],
        )

        self.assertTrue(self.checkpoint_file.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
