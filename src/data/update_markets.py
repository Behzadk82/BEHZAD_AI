# src/data/update_markets.py
# نسخه نهایی V4: مپ دقیق تمام بازارها، تخته‌ها و ابزارها
import sqlite3, requests, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH, HEADERS, TSETMC_BASE, TIMEOUT_MARKET_WATCH

# ============================================================
# مپ کامل کدهای TSETMC (کشف شده از خروجی‌های واقعی)
# ============================================================

# بازار
MARKET_MAP = {
    1: "بورس", 2: "فرابورس", 3: "بازار پایه", 4: "بورس کالا", 6: "بورس اوراق بهادار", 7: "بورس انرژی"
}

# تخته‌ها (cGrValCot) - طبق دیتای واقعی TSETMC
BOARD_MAP = {
    # --- بورس ---
    "N1": "بورس - بازار اول",
    "N2": "بورس - بازار دوم",
    "N4": "بورس - بازار چهارم",
    # --- پایه ---
    "Z1": "پایه - زرد", "1Z": "پایه - زرد", "2Z": "پایه - زرد",
    "O1": "پایه - نارنجی", "1O": "پایه - نارنجی",
    "R1": "پایه - قرمز", "1R": "پایه - قرمز",
    # --- فرابورس ---
    "A1": "فرابورس - بازار اول", "A2": "فرابورس - بازار دوم", "A3": "فرابورس - بازار سوم",
    # --- کدهای عددی که برای پایه/فرابورس هستند ---
    "13": "فرابورس - بازار پایه", "16": "فرابورس - بازار پایه", "17": "فرابورس - بازار پایه",
    "19": "فرابورس - بازار پایه", "20": "فرابورس - بازار پایه", "27": "فرابورس - بازار پایه",
    "31": "فرابورس - بازار پایه", "41": "فرابورس - بازار پایه", "47": "فرابورس - بازار پایه",
    "51": "فرابورس - بازار پایه", "52": "فرابورس - بازار پایه", "61": "فرابورس - بازار پایه",
    "71": "فرابورس - بازار پایه", "91": "فرابورس - بازار پایه",
    # --- کدهای کالایی ---
    "31A": "کالا", "G3": "کالا", "F3": "کالا", "U3": "کالا", "P1": "کالا",
    "T1": "کالا", "3A": "کالا", "1A": "کالا", "QS": "کالا", "QD": "کالا",
    "H1": "کالا", "ET": "کالا", "2A": "کالا", "T2": "کالا", "4A": "کالا",
    "E1": "کالا", "I1": "کالا", "QT": "کالا", "Q1": "کالا", "H2": "کالا",
    "C1": "کالا", "H4": "کالا", "F1": "کالا", "TJ": "کالا", "V1": "کالا",
    "TS": "کالا", "M1": "کالا", "5A": "کالا", "TA": "کالا", "L1": "کالا",
    "HN": "کالا", "W1": "کالا", "K2": "کالا", "FA": "کالا", "EZ": "کالا",
    "T6": "کالا", "T4": "کالا", "QR": "کالا", "NS": "کالا", "I2": "کالا",
    "TL": "کالا", "QB": "کالا", "P2": "کالا", "G1": "کالا", "EQ": "کالا",
    "EG": "کالا", "D1": "کالا", "5N": "کالا", "1N": "کالا",
}

def classify_instrument(symbol, name):
    name = name or ""
    if "صندوق" in name or "س." in name or "ETF" in name:
        return "صندوق"
    if any(x in name for x in ["اختيار", "اختیار", "آتي", "آتی"]):
        return "اختیار/آتی"
    if "حق تقدم" in name or "حقتقدم" in name:
        return "حق تقدم"
    if any(x in name for x in ["اوراق", "مرابحه", "صکوک", "خزانه"]):
        return "اوراق بدهی"
    return "سهام"

def update_markets():
    print("=" * 70)
    print("UPDATING SYMBOLS V4 (FULL MARKET MAP)")
    print("=" * 70)
    
    con = sqlite3.connect(DB_PATH, timeout=15)
    c = con.cursor()
    
    # اضافه کردن ستون‌ها
    for col in ["market", "board", "instrument_type"]:
        try:
            c.execute(f"ALTER TABLE symbols ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass
    con.commit()

    print("\n⏳ دریافت از TSETMC...")
    try:
        r = requests.get(f"{TSETMC_BASE}/ClosingPrice/GetMarketWatch", headers=HEADERS, timeout=TIMEOUT_MARKET_WATCH)
        r.raise_for_status()
        symbols = r.json().get("marketwatch", [])
    except Exception as e:
        print(f"❌ خطا: {e}"); con.close(); return

    print(f"✅ دریافت {len(symbols)} نماد.\n")

    for s in symbols:
        ins_code = str(s.get("insCode", ""))
        flow = s.get("flow", 0)
        cgr = str(s.get("cGrValCot", "")).strip()
        symbol = s.get("lva", "")
        name = s.get("lvc", "")
        
        # تعیین بازار و تخته
        market = MARKET_MAP.get(flow, "نامشخص")
        board = BOARD_MAP.get(cgr, "نامشخص")
        
        # تعیین نوع ابزار
        inst_type = classify_instrument(symbol, name)
        
        # اصلاح برای کالا (بعضی کدها واقعاً کالا هستن)
        if cgr in ["31A", "G3", "F3", "U3", "P1", "T1", "3A", "1A", "QS", "QD"]:
            if inst_type != "صندوق":
                inst_type = "کالا"
                market = "بورس کالا"
                board = "کالا"
        
        # آپدیت
        c.execute("SELECT ins_code FROM symbols WHERE ins_code = ?", (ins_code,))
        if c.fetchone():
            c.execute("UPDATE symbols SET market=?, board=?, instrument_type=? WHERE ins_code=?", (market, board, inst_type, ins_code))
        else:
            c.execute("INSERT INTO symbols (ins_code, symbol, name, market, board, instrument_type, updated_at) VALUES (?,?,?,?,?,?,datetime('now'))", (ins_code, symbol, name, market, board, inst_type))
    
    con.commit()
    
    print("=== تفکیک نهایی بازار ===")
    for row in c.execute("SELECT market, COUNT(*) FROM symbols GROUP BY market ORDER BY COUNT(*) DESC").fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    print("\n=== تفکیک نهایی تخته ===")
    for row in c.execute("SELECT board, COUNT(*) FROM symbols GROUP BY board ORDER BY COUNT(*) DESC").fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    print("\n=== تفکیک نهایی نوع ابزار ===")
    for row in c.execute("SELECT instrument_type, COUNT(*) FROM symbols GROUP BY instrument_type ORDER BY COUNT(*) DESC").fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    con.close()
    print("\nDONE!")

if __name__ == "__main__":
    update_markets()
