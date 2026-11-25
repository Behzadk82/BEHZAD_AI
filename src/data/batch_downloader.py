# src/data/batch_downloader.py
# Robust batch history downloader - Phase 3.1
# Downloads in batches of 500, with retry, checkpoint, and raw JSON backup.
# Rules:
#   - 403/429 -> STOP immediately (saves checkpoint)
#   - 500/502/503/504 -> retry up to 3 times
#   - Other errors -> log and continue to next symbol
#   - Every successful download is also saved to data/raw/{ins_code}.json

import json
import time
import sqlite3
import requests
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH, TSETMC_BASE, HEADERS, TIMEOUT_DAILY_LIST

CHECKPOINT_FILE = Path("data/batch_checkpoint.json")
RAW_DIR = Path("data/raw")
BATCH_SIZE = 500
MAX_RETRIES = 3
RETRY_STATUS_CODES = [500, 502, 503, 504]
STOP_STATUS_CODES = [403, 429]
DELAY_BETWEEN = 1.0


def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        with CHECKPOINT_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed": [], "failed": [], "batch_num": 0}


def save_checkpoint(state):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CHECKPOINT_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_all_symbols():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT ins_code, symbol FROM symbols ORDER BY trades DESC").fetchall()
    con.close()
    return [{"ins_code": r["ins_code"], "symbol": r["symbol"]} for r in rows]


def fetch_with_retry(session, url):
    """Fetch URL with retries. Returns (data, error_flag)."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=TIMEOUT_DAILY_LIST)
            
            # Stop codes - return immediately
            if r.status_code in STOP_STATUS_CODES:
                return None, f"STOP_{r.status_code}"
            
            # Retry codes
            if r.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
                wait = 2 ** attempt
                print(f"  [retry {attempt}] HTTP {r.status_code}, wait {wait}s", end=" ")
                time.sleep(wait)
                continue
            
            r.raise_for_status()
            data = r.json()
            records = data.get("closingPriceDaily", [])
            if not isinstance(records, list):
                return None, "INVALID_STRUCTURE"
            return records, None
        
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES:
                print(f"  [retry {attempt}] Timeout", end=" ")
                time.sleep(2 ** attempt)
            else:
                return None, "TIMEOUT"
        
        except requests.exceptions.ConnectionError:
            return None, "CONNECTION_ERROR"
        
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"  [retry {attempt}] {type(e).__name__}", end=" ")
                time.sleep(2 ** attempt)
            else:
                return None, str(e)
    
    return None, "MAX_RETRIES_EXCEEDED"


def save_raw_json(ins_code, records):
    """Save raw records to data/raw/{ins_code}.json for backup."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{ins_code}.json"
    if path.exists():
        return  # Don't overwrite
    with path.open("w", encoding="utf-8") as f:
        json.dump({"closingPriceDaily": records}, f, ensure_ascii=False)


def save_to_db(ins_code, records):
    if not records:
        return 0
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.execute("PRAGMA journal_mode=WAL")
    count = 0
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    
    with con:
        for raw in records:
            date = int(raw.get("dEven", 0))
            if date <= 0:
                continue
            con.execute("""
                INSERT INTO price_history (
                    ins_code, date, price_close, price_last, price_min, price_max,
                    price_first, price_yesterday, price_change, volume, value, trades, source, inserted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ins_code, date) DO NOTHING
            """, (
                ins_code, date,
                float(raw.get("pClosing", 0) or 0),
                float(raw.get("pDrCotVal", 0) or 0),
                float(raw.get("priceMin", 0) or 0),
                float(raw.get("priceMax", 0) or 0),
                float(raw.get("priceFirst", 0) or 0),
                float(raw.get("priceYesterday", 0) or 0),
                float(raw.get("priceChange", 0) or 0),
                float(raw.get("qTotTran5J", 0) or 0),
                float(raw.get("qTotCap", 0) or 0),
                float(raw.get("zTotTran", 0) or 0),
                "batch", now
            ))
            count += 1
    con.close()
    return count


def process_batch(batch, state, session, batch_num, total_pending):
    success = 0
    failed = 0
    stopped = False
    
    for i, sym in enumerate(batch, 1):
        ins_code = sym["ins_code"]
        symbol = sym["symbol"]
        print(f"[{i}/{len(batch)}] {symbol:15s} ...", end=" ")
        
        url = f"{TSETMC_BASE}/ClosingPrice/GetClosingPriceDailyList/{ins_code}/0"
        records, error = fetch_with_retry(session, url)
        
        if error and error.startswith("STOP_"):
            print(f"🛑 {error} - STOPPING BATCH")
            state["failed"].append({"ins_code": ins_code, "symbol": symbol, "error": error})
            save_checkpoint(state)
            stopped = True
            break
        
        if records:
            saved = save_to_db(ins_code, records)
            save_raw_json(ins_code, records)
            state["completed"].append(ins_code)
            success += 1
            print(f"✅ {saved} days")
        else:
            state["failed"].append({"ins_code": ins_code, "symbol": symbol, "error": error})
            failed += 1
            print(f"❌ {error}")
        
        time.sleep(DELAY_BETWEEN)
    
    return success, failed, stopped


def main():
    print("=" * 70)
    print("BATCH DOWNLOADER - Phase 3.1")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Max retries: {MAX_RETRIES}")
    print(f"  Stop codes: {STOP_STATUS_CODES}")
    print("=" * 70)
    print()
    
    state = load_checkpoint()
    symbols = get_all_symbols()
    
    # Filter out completed AND permanently failed
    completed_set = set(state["completed"])
    failed_set = {f["ins_code"] for f in state["failed"] if f["error"] in ("INVALID_STRUCTURE",)}
    pending = [s for s in symbols if s["ins_code"] not in completed_set and s["ins_code"] not in failed_set]
    
    print(f"📊 Total symbols: {len(symbols)}")
    print(f"✅ Completed: {len(state['completed'])}")
    print(f"❌ Failed: {len(state['failed'])}")
    print(f"⏳ Pending: {len(pending)}")
    print()
    
    if not pending:
        print("🎉 All done! No pending symbols.")
        return
    
    batch = pending[:BATCH_SIZE]
    state["batch_num"] += 1
    print(f"🚀 Starting batch #{state['batch_num']} with {len(batch)} symbols...")
    print()
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    success, failed, stopped = process_batch(batch, state, session, state["batch_num"], len(pending))
    
    # Save checkpoint after batch
    save_checkpoint(state)
    
    print()
    print("=" * 70)
    if stopped:
        print("🛑 BATCH STOPPED (rate limit / access denied)")
    else:
        print("✅ BATCH COMPLETE")
    print(f"  Success: {success}")
    print(f"  Failed: {failed}")
    print(f"  Total completed: {len(state['completed'])}/{len(symbols)}")
    print(f"  Remaining: {len(pending) - success}")
    print("=" * 70)


if __name__ == "__main__":
    main()
