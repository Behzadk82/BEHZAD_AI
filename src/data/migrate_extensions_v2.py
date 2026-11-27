# src/data/migrate_extensions_v2.py
# ستون‌های Volume Profile, Support/Resistance, Pivot Points

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

NEW_COLUMNS = [
    # Volume Profile
    ("vp_poc", "REAL"),
    ("vp_va_low", "REAL"),
    ("vp_va_high", "REAL"),
    # Support/Resistance
    ("nearest_support", "REAL"),
    ("nearest_resistance", "REAL"),
    # Pivot Points کلاسیک
    ("pivot", "REAL"),
    ("pivot_r1", "REAL"),
    ("pivot_r2", "REAL"),
    ("pivot_r3", "REAL"),
    ("pivot_s1", "REAL"),
    ("pivot_s2", "REAL"),
    ("pivot_s3", "REAL"),
    # Pivot Fibonacci
    ("pivot_fib_r1", "REAL"),
    ("pivot_fib_r2", "REAL"),
    ("pivot_fib_r3", "REAL"),
    ("pivot_fib_s1", "REAL"),
    ("pivot_fib_s2", "REAL"),
    ("pivot_fib_s3", "REAL"),
]


def migrate():
    print("=" * 60)
    print("EXTENSION V2: Volume Profile + Support/Resistance + Pivot")
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
    print(f"\n✅ {added} جدید، {existing} از قبل موجود")


if __name__ == "__main__":
    migrate()
