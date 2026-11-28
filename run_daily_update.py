# run_daily_update.py
import subprocess, sys

steps = [
    ("1. قیمت‌های جدید", "python src/data/incremental.py"),
    ("2. اندیکاتورهای روزانه", "python src/data/batch_advanced_indicators.py"),
    ("3. افزونه‌های پیشرفته", "python src/data/batch_extensions_v1.py"),
    ("4. Volume Profile و Pivot", "python src/data/batch_extensions_v2.py"),
    ("5. RVOL و Stoch RSI", "python src/data/batch_extensions_v3.py"),
    ("6. تایم‌فریم هفتگی/ماهانه", "python src/data/multi_timeframe_builder.py"),
    ("7. اندیکاتورهای هفتگی/ماهانه", "python src/analysis/indicators_multi_tf.py"),
]

for name, cmd in steps:
    print(f"\n{'='*60}\n{name}\n{'='*60}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"⚠️ Error in {name}")
