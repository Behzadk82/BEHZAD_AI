# src/data/migrate_extensions_v1.py
# افزونه ۱: Supertrend

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

NEW_COLUMNS = [
    ("supertrend", "REAL"),
    ("supertrend_direction", "TEXT"),  # UP / DOWN
    ("supertrend_upper", "REAL"),
    ("supertrend_lower", "REAL"),
]


def migrate():
    print("=" * 60)
    print("EXTENSION 1: Supertrend columns")
    print("=" * 60)
    
    con = sqlite3.connect(DB_PATH, timeout=15)
    c = con.cursor()
    
    added = 0
    existing = 0
    
    for col_name, col_type in NEW_COLUMNS:
        try:
            c.execute(f"ALTER TABLE indicators ADD COLUMN {col_name} {col_type}")
            added += 1
            print(f"✅ {col_name}")
        except sqlite3.OperationalError:
            existing += 1
            print(f"ℹ️ {col_name} از قبل موجود")
    
    con.commit()
    con.close()
    
    print()
    print(f"✅ {added} ستون جدید، {existing} از قبل موجود")


if __name__ == "__main__":
    migrate()
