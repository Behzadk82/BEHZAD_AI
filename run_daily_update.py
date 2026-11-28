import subprocess

steps = [
    ("1. قیمت جدید", "python src/data/incremental.py"),
    ("2. اندیکاتور روزانه", "python src/data/batch_advanced_indicators.py"),
    ("3. افزونه V1", "python src/data/batch_extensions_v1.py"),
    ("4. افزونه V2", "python src/data/batch_extensions_v2.py"),
    ("5. افزونه V3", "python src/data/batch_extensions_v3.py"),
    ("6. هفتگی/ماهانه", "python src/data/multi_timeframe_builder.py"),
    ("7. اندیکاتور چند تایم", "python src/analysis/indicators_multi_tf.py"),
]

for name, cmd in steps:
    print(f"\n{'='*60}\n{name}\n{'='*60}")
    r = subprocess.run(cmd, shell=True)
    if r.returncode != 0: print(f"⚠️ خطا در {name}")
