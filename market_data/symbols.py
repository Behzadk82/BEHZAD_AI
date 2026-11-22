
import json
import os
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from urllib.parse import urlparse


class SymbolManager:
    """
    دریافت و اعتبارسنجی فهرست نمادها.
    این ماژول صرفاً برای جمع‌آوری و تحلیل اطلاعات است.
    """

    ALLOWED_HOSTS = {
        "www.tsetmc.com",
        "tsetmc.com",
        "cdn.tsetmc.com"
    }

    def __init__(self, timeout=20):
        self.timeout = timeout

    def validate_url(self, url):
        parsed = urlparse(url)

        return (
            parsed.scheme == "https"
            and parsed.hostname in self.ALLOWED_HOSTS
        )

    def fetch_data(self):
        url = os.environ.get("TSETMC_SYMBOLS_URL", "").strip()

        if not url:
            return {
                "success": False,
                "error": "symbols_url_not_configured",
                "message": "آدرس API فهرست نمادها هنوز تنظیم نشده است."
            }

        if not self.validate_url(url):
            return {
                "success": False,
                "error": "invalid_source_url",
                "message": "آدرس منبع اطلاعات معتبر نیست."
            }

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 BEHZAD_AI/0.4",
                "Accept": "application/json"
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

                raw = response.read(10 * 1024 * 1024)

                if len(raw) >= 10 * 1024 * 1024:
                    return {
                        "success": False,
                        "error": "response_too_large"
                    }

                return {
                    "success": True,
                    "data": json.loads(raw.decode("utf-8"))
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
                "data",
                "instruments",
                "result",
                "instrumentList",
                "instrument"
            ):
                value = data.get(key)

                if isinstance(value, list):
                    return value

        return []

    def normalize_symbol(self, item):
        if not isinstance(item, dict):
            return None

        symbol = (
            item.get("lVal18AFC")
            or item.get("symbol")
            or item.get("ticker")
            or item.get("insCode")
        )

        name = (
            item.get("lVal30")
            or item.get("name")
            or item.get("instrumentName")
            or symbol
        )

        if symbol is None:
            return None

        symbol = str(symbol).strip()
        name = str(name).strip()

        if not symbol or not name:
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
            "symbol": symbol,
            "name": name
        }

    def validate_symbols(self, data):
        rows = self.extract_rows(data)

        valid = []
        rejected = 0
        seen = set()

        for item in rows:
            normalized = self.normalize_symbol(item)

            if normalized is None:
                rejected += 1
                continue

            key = normalized["symbol"]

            if key in seen:
                continue

            seen.add(key)
            valid.append(normalized)

        return {
            "success": True,
            "total_received": len(rows),
            "valid_count": len(valid),
            "rejected_count": rejected,
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
    result = manager.get_symbols()

    print(json.dumps(
        result,
        ensure_ascii=False,
        indent=2
    ))
      
