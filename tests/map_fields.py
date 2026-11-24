# map_fields.py
# Discover the real field names from each TSETMC endpoint.
# VPN must be OFF.

import requests
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://cdn.tsetmc.com/",
}

session = requests.Session()
session.headers.update(headers)

FOLAD = "46348559193224090"

# Each endpoint we want to map
endpoints = {
    "MarketWatch": "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch",
    f"ClosingPriceInfo (FOLAD)": f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{FOLAD}",
    f"DailyList (FOLAD)": f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{FOLAD}/0",
    f"InstrumentInfo (FOLAD)": f"https://cdn.tsetmc.com/api/Instrument/GetInstrumentInfo/{FOLAD}",
}

print("=" * 70)
print("TSETMC FIELD MAPPER")
print("=" * 70)

for name, url in endpoints.items():
    print(f"\n{'=' * 70}")
    print(f"ENDPOINT: {name}")
    print(f"URL: {url}")
    print("-" * 70)
    
    try:
        r = session.get(url, timeout=40)
        print(f"Status: {r.status_code}, Size: {len(r.text)} chars")
        
        if r.status_code != 200:
            print(f"[SKIP] Non-200 status")
            continue
        
        data = r.json()
        
        # Unwrap the main container
        if isinstance(data, dict):
            keys = list(data.keys())
            print(f"Top keys: {keys}")
            
            # Find the main data container
            main_key = keys[0] if keys else None
            if main_key:
                payload = data[main_key]
                
                # Case 1: payload is a list
                if isinstance(payload, list):
                    print(f"\n{main_key}: list of {len(payload)} items")
                    if payload:
                        first = payload[0]
                        if isinstance(first, dict):
                            print(f"\nField names in first item ({len(first)} fields):")
                            for k, v in first.items():
                                print(f"  {k:20s} = {str(v)[:60]}")
                
                # Case 2: payload is a dict
                elif isinstance(payload, dict):
                    print(f"\n{main_key}: dict with {len(payload)} fields")
                    print(f"\nField names:")
                    for k, v in payload.items():
                        print(f"  {k:20s} = {str(v)[:60]}")
        
        elif isinstance(data, list):
            print(f"Root is list of {len(data)} items")
            if data and isinstance(data[0], dict):
                print(f"\nField names in first item:")
                for k, v in data[0].items():
                    print(f"  {k:20s} = {str(v)[:60]}")
    
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")

print("\n" + "=" * 70)
print("MAP COMPLETE")
print("=" * 70)
