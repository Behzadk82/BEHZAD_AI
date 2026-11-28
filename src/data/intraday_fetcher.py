# src/data/intraday_fetcher.py
# دریافت داده‌های زیر-روزانه (1m-90m) با yfinance-ir
import sys, sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

try:
    from yfinance_ir import Ticker
except ImportError:
    print("❌ yfinance-ir نصب نیست. اول نصب کن: pip install yfinance-ir")
    sys.exit(1)

def fetch_intraday(symbol_name, interval="15m"):
    """دریافت داده زیر-روزانه برای یک نماد"""
    try:
        t = Ticker(symbol_name)
        # yfinance-ir از تاریخچه معاملات، کندل می‌سازه
        hist = t.history(period="1mo", interval=interval)
        if hist is None or hist.empty:
            return None
        return hist
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("=" * 60)
    print("INTRADAY FETCHER (yfinance-ir)")
    print("=" * 60)
    print("⚠️ این فقط تست است. برای ذخیره، باید جدول جداگانه بسازیم.")
    
    # تست روی فولاد
    hist = fetch_intraday("فولاد", interval="15m")
    if hist is not None:
        print(f"✅ دریافت {len(hist)} کندل ۱۵ دقیقه‌ای")
        print(hist.tail())
    else:
        print("❌ داده‌ای دریافت نشد")

if __name__ == "__main__":
    main()
