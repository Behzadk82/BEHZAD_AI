# src/data/migrate_indicators_v2.py
# اضافه کردن ستون‌های اندیکاتورهای پیشرفته به جدول indicators

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

# ستون‌های جدید برای جدول indicators
NEW_COLUMNS = [
    # ATR
    ("atr14", "REAL"),
    # ADX
    ("adx14", "REAL"),
    ("plus_di", "REAL"),
    ("minus_di", "REAL"),
    # OBV
    ("obv", "REAL"),
    # Stochastic
    ("stoch_k", "REAL"),
    ("stoch_d", "REAL"),
    # Ichimoku
    ("ichimoku_tenkan", "REAL"),
    ("ichimoku_kijun", "REAL"),
    ("ichimoku_senkou_a", "REAL"),
    ("ichimoku_senkou_b", "REAL"),
    # Fibonacci
    ("fib_236", "REAL"),
    ("fib_382", "REAL"),
    ("fib_500", "REAL"),
    ("fib_618", "REAL"),
    ("fib_786", "REAL"),
    # VWAP
    ("vwap", "REAL"),
    # CCI
    ("cci20", "REAL"),
    # MFI
    ("mfi14", "REAL"),
    # Williams %R
    ("williams_r", "REAL"),
    # ROC
    ("roc12", "REAL"),
    # Parabolic SAR
    ("psar", "REAL"),
    # حقیقی/حقوقی (فعلاً خالی - بعداً از API پر می‌شه)
    ("buy_i_volume", "REAL"),
    ("sell_i_volume", "REAL"),
    ("buy_n_volume", "REAL"),
    ("sell_n_volume", "REAL"),
    ("buy_count_i", "REAL"),
    ("buy_count_n", "REAL"),
    ("sell_count_i", "REAL"),
    ("sell_count_n", "REAL"),
    # Money Flow Index
    ("money_flow_ratio", "REAL"),
    # وضعیت روند
    ("trend_direction", "TEXT"),  # UP / DOWN / SIDEWAYS
    ("trend_strength", "TEXT"),   # STRONG / WEAK
]


def migrate():
    print("=" * 60)
    print("MIGRATING indicators TABLE - Adding 30+ advanced columns")
    print("=" * 60)
    
    con = sqlite3.connect(DB_PATH, timeout=15)
    c = con.cursor()
    
    added = 0
    existing = 0
    
    for col_name, col_type in NEW_COLUMNS:
        try:
            c.execute(f"ALTER TABLE indicators ADD COLUMN {col_name} {col_type}")
            added += 1
            print(f"✅ {col_name} ({col_type})")
        except sqlite3.OperationalError:
            existing += 1
            print(f"ℹ️ {col_name} از قبل وجود دارد")
    
    con.commit()
    con.close()
    
    print()
    print("=" * 60)
    print(f"✅ {added} ستون جدید اضافه شد")
    print(f"ℹ️ {existing} ستون از قبل موجود بود")
    print("=" * 60)


if __name__ == "__main__":
    migrate()
