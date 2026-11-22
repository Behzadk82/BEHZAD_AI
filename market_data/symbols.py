
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from urllib.parse import urlencode


class SymbolManager:
    """دریافت و اعتبارسنجی فهرست ابزارهای بازار از TSETMC."""

    BASE_URL = (
        "https://cdn.tsetmc.com/api/"
        "ClosingPrice/GetMarketWatch"
    )

    MAX_RESPONSE_SIZE = 10 * 1024 * 1024

    def __init__(self, timeout=25):
        self.timeout = timeout

    def build_url(self):
        params = [
            ("market", "0"),
            ("withBestLimits", "false"),
            ("hEven", "0"),
            ("RefID", "0"),
        ]

        for i in range(9):
            params.append((f"paperTypes[{i}]", str(i + 1)))

        return self.BASE_URL + "?" + urlencode(params)

    def fetch_data(self):
        request = urllib.request.Request(
            self.build_url(),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/126 Safari/537.36"
                ),
                "Accept": "application/json",
                "Referer": "https://www.tsetmc.com/",
                "Origin": "https://www.tsetmc.com"
            }
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout
            ) as response:

                if response.status != 200:
                    return {
                        "success": False,
                        "error": "http_error",
                        "http_status": response.status
                    }

                raw = response.read(
                    self.MAX_RESPONSE_SIZE + 1
                )

                if len(raw) > self.MAX_RESPONSE_SIZE:
                    return {
                        "success": False,
                        "error": "response_too_large"
                    }

                try:
                    data = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return {
                        "success": False,
                        "error": "invalid_json_response"
                    }

                return {
                    "success": True,
                    "data": data
                }

        except urllib.error.HTTPError as error:
            return {
                "success": False,
                "error": "http_error",
                "http_status": error.code
            }

        except Exception as error:
            return {
                "success": False,
                "error": "fetch_failed",
                "error_type": type(error).__name__
            }

    def extract_rows(self, data):
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            for key in (
                "marketwatch",
                "data",
                "instruments",
                "result",
                "instrumentList"
            ):
                value = data.get(key)

                if isinstance(value, list):
                    return value

                if isinstance(value, dict):
                    for nested in value.values():
                        if isinstance(nested, list):
                            return nested

        return []

    def normalize_symbol(self, item):
        if not isinstance(item, dict):
            return None

        symbol = item.get("lVal18AFC")
        name = item.get("lVal30")
        code = item.get("insCode")

        if not symbol or not code:
            return None

        symbol = str(symbol).strip()
        name = str(name or symbol).strip()
        code = str(code).strip()

        if not symbol or not code or not name:
            return None

        if not code.isdigit():
            return None

        if len(symbol) > 100 or len(name) > 250:
            return None

        if not re.fullmatch(
            r"[\w\u0600-\u06FF\u200c.-]+",
            symbol,
            flags=re.UNICODE
        ):
            return None

        return {
            "instrument_code": code,
            "symbol": symbol,
            "name": name
        }

    def validate_symbols(self, data):
        rows = self.extract_rows(data)

        if not rows:
            return {
                "success": False,
                "error": "unexpected_data_structure",
                "message": "ساختار پاسخ API قابل شناسایی نیست."
            }

        valid = []
        rejected = 0
        duplicates = 0
        seen = set()

        for item in rows:
            normalized = self.normalize_symbol(item)

            if normalized is None:
                rejected += 1
                continue

            code = normalized["instrument_code"]

            if code in seen:
                duplicates += 1
                continue

            seen.add(code)
            valid.append(normalized)

        return {
            "success": True,
            "source": "TSETMC",
            "total_received": len(rows),
            "valid_count": len(valid),
            "rejected_count": rejected,
            "duplicate_count": duplicates,
            "symbols": valid,
            "checked_at": datetime.now(
                timezone.utc
            ).isoformat()
        }

    def get_symbols(self):
        result = self.fetch_data()

        if not result["success"]:
            return result

        return self.validate_symbols(result["data"])


if __name__ == "__main__":
    manager = SymbolManager()

    print(json.dumps(
        manager.get_symbols(),
        ensure_ascii=False,
        indent=2
    ))
                    
