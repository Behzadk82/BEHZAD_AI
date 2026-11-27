import tempfile
import unittest
from pathlib import Path

from src.data.database import Database


class TestDatabaseCRUD(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db = Database(self.db_path)
        self.db.connect()
        self.db.init_schema()

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_schema_tables_and_index(self):
        con = self.db.conn

        tables = {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        self.assertIn("symbols", tables)
        self.assertIn("fetch_log", tables)

        indexes = {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
        }
        self.assertIn("idx_symbols_symbol", indexes)

        columns = con.execute("PRAGMA table_info(symbols)").fetchall()
        ins_code = next(c for c in columns if c["name"] == "ins_code")
        self.assertEqual(ins_code["pk"], 1)

    def test_insert_symbol(self):
        count = self.db.upsert_symbols([
            {
                "ins_code": "1001",
                "symbol": "TEST1",
                "name": "Test Company",
                "last_price": 120,
                "close_price": 118,
                "volume": 5000,
                "trades": 25,
            }
        ])

        self.assertEqual(count, 1)
        self.assertEqual(self.db.count_symbols(), 1)

        row = self.db.get_symbol("1001")
        self.assertIsNotNone(row)
        self.assertEqual(row["symbol"], "TEST1")
        self.assertEqual(row["last_price"], 120)

    def test_upsert_updates_without_duplicate(self):
        original = {
            "ins_code": "2001",
            "symbol": "OLD",
            "name": "Old Name",
            "last_price": 10,
            "trades": 5,
        }
        updated = {
            "ins_code": "2001",
            "symbol": "NEW",
            "name": "New Name",
            "last_price": 20,
            "trades": 50,
        }

        self.db.upsert_symbols([original])
        count = self.db.upsert_symbols([updated])

        self.assertEqual(count, 1)
        self.assertEqual(self.db.count_symbols(), 1)

        row = self.db.get_symbol("2001")
        self.assertEqual(row["symbol"], "NEW")
        self.assertEqual(row["name"], "New Name")
        self.assertEqual(row["last_price"], 20)
        self.assertEqual(row["trades"], 50)

    def test_missing_symbol_returns_none(self):
        self.assertIsNone(self.db.get_symbol("DOES_NOT_EXIST"))

    def test_list_symbols_order_and_limit(self):
        self.db.upsert_symbols([
            {"ins_code": "A", "symbol": "A", "trades": 10},
            {"ins_code": "B", "symbol": "B", "trades": 30},
            {"ins_code": "C", "symbol": "C", "trades": 20},
        ])

        result = self.db.list_symbols(limit=2)

        self.assertEqual(len(result), 2)
        self.assertEqual(
            [row["ins_code"] for row in result],
            ["B", "C"],
        )

    def test_empty_ins_code_is_skipped(self):
        count = self.db.upsert_symbols([
            {"symbol": "INVALID", "name": "Missing Code"},
            {"ins_code": "", "symbol": "EMPTY"},
            {"ins_code": "VALID", "symbol": "VALID"},
        ])

        self.assertEqual(count, 1)
        self.assertEqual(self.db.count_symbols(), 1)
        self.assertIsNone(self.db.get_symbol(""))

    def test_fetch_log_and_stats(self):
        self.db.upsert_symbols([
            {"ins_code": "T1", "symbol": "T1", "trades": 10},
            {"ins_code": "T2", "symbol": "T2", "trades": 0},
        ])

        self.db.log_fetch(
            "TEST_SOURCE",
            2,
            "Isolated CRUD test",
        )

        stats = self.db.stats()

        self.assertEqual(stats["total_symbols"], 2)
        self.assertEqual(stats["with_trades"], 1)
        self.assertEqual(stats["fetch_logs"], 1)
        self.assertGreater(stats["db_size_kb"], 0)

        log = self.db.conn.execute(
            "SELECT * FROM fetch_log"
        ).fetchone()

        self.assertEqual(log["source"], "TEST_SOURCE")
        self.assertEqual(log["record_count"], 2)
        self.assertEqual(log["notes"], "Isolated CRUD test")

    def test_delete_in_temporary_database(self):
        self.db.upsert_symbols([
            {"ins_code": "DELETE_ME", "symbol": "DEL"},
            {"ins_code": "KEEP", "symbol": "KEEP"},
        ])

        self.db.conn.execute(
            "DELETE FROM symbols WHERE ins_code = ?",
            ("DELETE_ME",),
        )
        self.db.conn.commit()

        self.assertIsNone(self.db.get_symbol("DELETE_ME"))
        self.assertIsNotNone(self.db.get_symbol("KEEP"))
        self.assertEqual(self.db.count_symbols(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
