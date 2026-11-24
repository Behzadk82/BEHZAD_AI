# src/data/tsetmc.py
# TSETMC data fetcher module - Phase 1.1
# Handles all communication with TSETMC API

import requests
import time
from typing import Optional, Dict, Any


class TSETMCClient:
    """Client for fetching data from TSETMC API"""

    BASE_URL = "https://cdn.tsetmc.com/api"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://cdn.tsetmc.com/",
        })

    def get_closing_price(self, ins_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch closing price info for a given instrument code.

        Args:
            ins_code: TSETMC instrument code (e.g., "46348559193224090" for FOLAD)

        Returns:
            dict with closing price data, or None on error
        """
        url = f"{self.BASE_URL}/ClosingPrice/GetClosingPriceInfo/{ins_code}"

        try:
            r = self.session.get(url, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            return data.get("closingPriceInfo")

        except requests.exceptions.Timeout:
            print(f"[ERROR] Timeout for ins_code={ins_code}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] Connection failed for ins_code={ins_code} (check VPN)")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"[ERROR] HTTP error for ins_code={ins_code}: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected: {type(e).__name__}: {e}")
            return None

    def get_symbol_info(self, ins_code: str) -> Optional[Dict[str, Any]]:
        """
        Fetch general symbol info (name, market, etc).
        """
        url = f"{self.BASE_URL}/Instrument/GetInstrumentInfo/{ins_code}"

        try:
            r = self.session.get(url, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            return data.get("instrumentInfo")

        except Exception as e:
            print(f"[ERROR] get_symbol_info failed: {type(e).__name__}: {e}")
            return None


# --- Simple test when run directly ---
if __name__ == "__main__":
    client = TSETMCClient()
    ins_code = "46348559193224090"  # FOLAD

    print("Testing TSETMCClient...")
    print("-" * 50)

    cp = client.get_closing_price(ins_code)
    if cp:
        print("SUCCESS")
        print(f"pClosing:   {cp.get('pClosing')}")
        print(f"pDrCotVal:  {cp.get('pDrCotVal')}")
        print(f"qTotTran5J: {cp.get('qTotTran5J')}")
        print(f"zTotTran:   {cp.get('zTotTran')}")
        print(f"dEven:      {cp.get('dEven')}")
    else:
        print("FAILED - no data returned")
