# src/data/symbols.py
# Fetch all symbols from TSETMC MarketWatch - Phase 1.1.2
# Uses the correct endpoint discovered through testing.

import requests
import json
import os
from typing import Optional, List, Dict, Any


class SymbolFetcher:
    """Fetches all symbols from TSETMC MarketWatch endpoint"""

    BASE_URL = "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch"

    def __init__(self, timeout: int = 40):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://cdn.tsetmc.com/",
        })

    def get_all_symbols(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch all symbols from MarketWatch."""
        try:
            r = self.session.get(self.BASE_URL, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            return data.get("marketwatch", [])
        except requests.exceptions.Timeout:
            print("[ERROR] Timeout - check VPN or internet")
            return None
        except requests.exceptions.ConnectionError:
            print("[ERROR] Connection failed - turn off VPN")
            return None
        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {e}")
            return None

    @staticmethod
    def extract_symbol_info(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a raw MarketWatch record."""
        return {
            "ins_code": str(raw.get("insCode", "")),
            "symbol": raw.get("lva", ""),
            "name": raw.get("lvc", ""),
            "last_price": raw.get("pdv", 0),
            "close_price": raw.get("pc", 0),
            "yesterday_price": raw.get("py", 0),
            "volume": raw.get("qtj", 0),
            "value": raw.get("qtc", 0),
            "trades": raw.get("ztt", 0),
            "eps": raw.get("eps", 0),
            "pe": raw.get("pe", None),
        }


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    fetcher = SymbolFetcher()
    print("Fetching all symbols from TSETMC MarketWatch...")
    print("-" * 60)

    symbols = fetcher.get_all_symbols()

    if symbols:
        print(f"TOTAL: {len(symbols)} symbols fetched")
        print("-" * 60)

        # Extract all to normalized form
        normalized = [fetcher.extract_symbol_info(s) for s in symbols]

        # Filter empty ins_codes
        normalized = [s for s in normalized if s["ins_code"]]

        print(f"VALID (with ins_code): {len(normalized)}")
        print()
        print("First 10 symbols:")
        for i, s in enumerate(normalized[:10], 1):
            print(f"  {i}. {s['symbol']:15s} | {s['name'][:30]:30s} | price={s['last_price']}")

        # Save raw
        with open("data/market_watch_raw.json", "w", encoding="utf-8") as f:
            json.dump(symbols, f, ensure_ascii=False, indent=2)
        print(f"\nRaw saved: data/market_watch_raw.json ({len(symbols)} records)")

        # Save normalized
        with open("data/symbols.json", "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
        print(f"Normalized saved: data/symbols.json ({len(normalized)} records)")

        # Market breakdown (approximate - by lvc patterns)
        print()
        print("Sample from different categories:")
        fund_count = sum(1 for s in normalized if "صندوق" in s["name"])
        option_count = sum(1 for s in normalized if "اختيار" in s["name"] or "اختیار" in s["name"])
        bond_count = sum(1 for s in normalized if "اوراق" in s["name"] or "مرابحه" in s["name"])
        print(f"  Funds (صندوق): ~{fund_count}")
        print(f"  Options (اختیار): ~{option_count}")
        print(f"  Bonds (اوراق): ~{bond_count}")
        print(f"  Other (likely stocks): ~{len(normalized) - fund_count - option_count - bond_count}")

    else:
        print("FAILED - no data fetched")
