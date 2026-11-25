# src/data/history.py
# Fetch daily price history for a symbol - Phase 1.2
# Uses GetClosingPriceDailyList endpoint.
# VPN must be OFF.

import requests
import json
from typing import Optional, List, Dict, Any


class HistoryFetcher:
    """Fetches daily price history from TSETMC"""

    BASE_URL = "https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList"

    def __init__(self, timeout: int = 40):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://cdn.tsetmc.com/",
        })

    def get_history(self, ins_code: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch full daily history for a symbol."""
        url = f"{self.BASE_URL}/{ins_code}/0"
        try:
            r = self.session.get(url, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            records = data.get("closingPriceDaily", [])
            if not isinstance(records, list):
                print(f"[ERROR] Unexpected structure for {ins_code}")
                return None
            return records
        except requests.exceptions.Timeout:
            print(f"[ERROR] Timeout for {ins_code}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] Connection failed - check VPN")
            return None
        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {e}")
            return None

    @staticmethod
    def extract_history_record(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a daily history record."""
        return {
            "date": int(raw.get("dEven", 0)),
            "price_close": float(raw.get("pClosing", 0) or 0),
            "price_last": float(raw.get("pDrCotVal", 0) or 0),
            "price_min": float(raw.get("priceMin", 0) or 0),
            "price_max": float(raw.get("priceMax", 0) or 0),
            "price_first": float(raw.get("priceFirst", 0) or 0),
            "price_yesterday": float(raw.get("priceYesterday", 0) or 0),
            "price_change": float(raw.get("priceChange", 0) or 0),
            "volume": float(raw.get("qTotTran5J", 0) or 0),
            "value": float(raw.get("qTotCap", 0) or 0),
            "trades": float(raw.get("zTotTran", 0) or 0),
        }


if __name__ == "__main__":
    # Quick test with FOLAD
    ins_code = "46348559193224090"
    fetcher = HistoryFetcher()

    print("Fetching history for FOLAD (فولاد)...")
    print("-" * 60)

    records = fetcher.get_history(ins_code)

    if records:
        print(f"TOTAL RECORDS: {len(records)}")

        # Normalize
        normalized = [fetcher.extract_history_record(r) for r in records]
        normalized = [r for r in normalized if r["date"] > 0]
        normalized.sort(key=lambda r: r["date"])

        print(f"VALID RECORDS: {len(normalized)}")
        print(f"OLDEST DATE: {normalized[0]['date']}")
        print(f"LATEST DATE: {normalized[-1]['date']}")

        print("\nLAST 5 DAYS:")
        for r in normalized[-5:]:
            print(f"  {r['date']} | close={r['price_close']} | vol={int(r['volume'])} | trades={int(r['trades'])}")

        # Save raw
        with open("data/history_FOLAD_raw.json", "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False)
        print(f"\nRaw saved: data/history_FOLAD_raw.json ({len(records)} records)")

        # Save normalized
        with open("data/history_FOLAD.json", "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
        print(f"Normalized saved: data/history_FOLAD.json ({len(normalized)} records)")

    else:
        print("FAILED - no data fetched")
