import sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

NEW_COLUMNS = [
    ("stoch_rsi", "REAL"), ("wma20", "REAL"), ("vwma20", "REAL"),
    ("rvol", "REAL"), ("aroon_up", "REAL"),
    ("aroon_down", "REAL"), ("aroon_osc", "REAL"),
]

def migrate():
    con = sqlite3.connect(DB_PATH, timeout=15)
    c = con.cursor()
    for col_name, col_type in NEW_COLUMNS:
        try:
            c.execute(f"ALTER TABLE indicators ADD COLUMN {col_name} {col_type}")
            print(f"OK: {col_name}")
        except sqlite3.OperationalError:
            print(f"EXISTS: {col_name}")
    con.commit()
    con.close()

if __name__ == "__main__":
    migrate()
