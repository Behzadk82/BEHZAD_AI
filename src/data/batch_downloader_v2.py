# src/data/batch_downloader_v2.py
# دانلود تاریخچه فقط برای نمادهایی که ندارن
import json, sqlite3, sys, time, requests
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH, TSETMC_BASE, HEADERS, TIMEOUT_DAILY_LIST

CHECKPOINT = Path("data/batch_checkpoint_v2.json")
BATCH_SIZE = 500

def load_checkpoint():
    if CHECKPOINT.exists():
        with CHECKPOINT.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed": [], "failed": []}

def save_checkpoint(state):
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    with CHECKPOINT.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_pending_symbols():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    # نمادهایی که تاریخچه ندارن
    rows = con.execute("""
        SELECT s.ins_code, s.symbol FROM symbols s
        LEFT JOIN price_history p ON s.ins_code = p.ins_code
        WHERE p.ins_code IS NULL
    """).fetchall()
    con.close()
    return [{"ins_code": r["ins_code"], "symbol": r["symbol"]} for r in rows]

def fetch_history(ins_code):
    url = f"{TSETMC_BASE}/ClosingPrice/GetClosingPriceDailyList/{ins_code}/0"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT_DAILY_LIST)
        if r.status_code in (403, 429): return None, f"STOP_{r.status_code}"
        if r.status_code != 200: return None, f"HTTP_{r.status_code}"
        data = r.json()
        records = data.get("closingPriceDaily", [])
        return records if isinstance(records, list) else None, None
    except Exception as e:
        return None, str(e)

def save_to_db(ins_code, records):
    if not records: return 0
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.execute("PRAGMA journal_mode=WAL")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    count = 0
    with con:
        for raw in records:
            try:
                date = int(raw.get("dEven", 0))
                if date <= 0: continue
                con.execute("""
                    INSERT INTO price_history (ins_code, date, price_close, price_last, price_min, price_max,
                        price_first, price_yesterday, price_change, volume, value, trades, source, inserted_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(ins_code, date) DO NOTHING
                """, (ins_code, date,
                    float(raw.get("pClosing", 0) or 0), float(raw.get("pDrCotVal", 0) or 0),
                    float(raw.get("priceMin", 0) or 0), float(raw.get("priceMax", 0) or 0),
                    float(raw.get("priceFirst", 0) or 0), float(raw.get("priceYesterday", 0) or 0),
                    float(raw.get("priceChange", 0) or 0), float(raw.get("qTotTran5J", 0) or 0),
                    float(raw.get("qTotCap", 0) or 0), float(raw.get("zTotTran", 0) or 0),
                    "batch_v2", now))
                if con.total_changes > count: count += 1
            except: continue
    con.close()
    return count

def main():
    print("=" * 60)
    print("BATCH DOWNLOADER V2 - فقط نمادهای بدون تاریخچه")
    print("=" * 60)
    
    state = load_checkpoint()
    pending = get_pending_symbols()
    completed_set = set(state["completed"])
    pending = [s for s in pending if s["ins_code"] not in completed_set]
    
    print(f"نمادهای بدون تاریخچه: {len(pending)}")
    print(f"قبلاً دانلود شده: {len(state['completed'])}")
    print(f"بسته فعلی: {min(BATCH_SIZE, len(pending))}")
    print()
    
    if not pending:
        print("🎉 همه نمادها تاریخچه دارن!")
        return
    
    batch = pending[:BATCH_SIZE]
    success = 0; failed = 0; stopped = False
    session = requests.Session()
    session.headers.update(HEADERS)
    
    for i, sym in enumerate(batch, 1):
        print(f"[{i}/{len(batch)}] {sym['symbol']:15s} ...", end=" ")
        records, error = fetch_history(sym["ins_code"])
        
        if error and error.startswith("STOP_"):
            print(f"🛑 {error}")
            stopped = True
            break
        
        if records:
            saved = save_to_db(sym["ins_code"], records)
            state["completed"].append(sym["ins_code"])
            success += 1
            print(f"✅ {saved} روز")
        else:
            state["failed"].append({"ins_code": sym["ins_code"], "error": error})
            failed += 1
            print(f"❌ {error}")
        
        time.sleep(0.5)  # ادب به سرور
    
    save_checkpoint(state)
    print()
    print("=" * 60)
    print(f"✅ موفق: {success} | ❌ ناموفق: {failed} | 🛑 متوقف: {stopped}")
    print(f"کل تکمیل‌شده: {len(state['completed'])}")
    print("=" * 60)

if __name__ == "__main__":
    main()
