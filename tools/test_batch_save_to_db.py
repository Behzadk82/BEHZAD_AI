import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.data import batch_downloader as batch


def record(**overrides):
    item = {
        "dEven": 20250115,
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
    item.update(overrides)
    return item


class BatchSaveToDBIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")

        con = sqlite3.connect(self.db_path)
        con.execute("""
            CREATE TABLE price_history (
                ins_code TEXT NOT NULL,
                date INTEGER NOT NULL,
                price_close REAL,
                price_last REAL,
                price_min REAL,
                price_max REAL,
                price_first REAL,
                price_yesterday REAL,
                price_change REAL,
                volume REAL,
                value REAL,
                trades REAL,
                source TEXT,
                inserted_at TEXT,
                UNIQUE(ins_code, date)
            )
        """)
        con.commit()
        con.close()

        self.db_patch = patch.object(
            batch, "DB_PATH", self.db_path
        )
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def read_rows(self):
        con = sqlite3.connect(self.db_path)
        try:
            return con.execute(
                "SELECT * FROM price_history ORDER BY date"
            ).fetchall()
        finally:
            con.close()

    def test_real_insert_returns_actual_insert_count(self):
        inserted = batch.save_to_db(
            "TEST001",
            [record()],
        )

        rows = self.read_rows()

        self.assertEqual(inserted, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "TEST001")
        self.assertEqual(rows[0][1], 20250115)
        self.assertEqual(rows[0][2], 100)
        self.assertEqual(rows[0][3], 105)
        self.assertEqual(rows[0][12], "batch")
        self.assertTrue(rows[0][13])

    def test_invalid_record_is_not_inserted(self):
        invalid_records = [
            record(dEven=20250229),
            record(pClosing=-1),
            record(qTotTran5J=-1),
            record(pClosing=0, pDrCotVal=0),
            record(pClosing=float("nan")),
        ]

        inserted = batch.save_to_db(
            "TEST002",
            invalid_records,
        )

        self.assertEqual(inserted, 0)
        self.assertEqual(self.read_rows(), [])

    def test_duplicate_date_is_not_overwritten(self):
        first = record(pClosing=100, pDrCotVal=105)
        second = record(pClosing=999, pDrCotVal=999)

        first_inserted = batch.save_to_db(
            "TEST003",
            [first],
        )

        second_inserted = batch.save_to_db(
            "TEST003",
            [second],
        )

        rows = self.read_rows()

        self.assertEqual(first_inserted, 1)
        self.assertEqual(second_inserted, 0)
        self.assertEqual(len(rows), 1)

        # Original data must remain unchanged.
        self.assertEqual(rows[0][2], 100)
        self.assertEqual(rows[0][3], 105)

    def test_price_fallback_is_saved_correctly(self):
        item = record(
            pClosing=0,
            pDrCotVal=123,
        )

        inserted = batch.save_to_db(
            "TEST004",
            [item],
        )

        rows = self.read_rows()

        self.assertEqual(inserted, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], 123)
        self.assertEqual(rows[0][3], 123)

    def test_mixed_records_actual_insert_count(self):
        items = [
            record(dEven=20250115),
            record(dEven=20250116, pClosing=-10),
            record(dEven=20250117, pClosing=0, pDrCotVal=120),
            record(dEven=20250229),
        ]

        inserted = batch.save_to_db(
            "TEST005",
            items,
        )

        rows = self.read_rows()

        self.assertEqual(inserted, 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            [row[1] for row in rows],
            [20250115, 20250117],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
