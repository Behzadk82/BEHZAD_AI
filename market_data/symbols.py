
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from urllib.parse import urlencode


class SymbolManager:
    """دریافت، اعتبارسنجی و طبقه‌بندی ابزارهای بازار TSETMC."""

    BASE_URL = (
        "https://cdn.tsetmc.com/api/"
        "ClosingPrice/GetMarketWatch"
    )

    MAX_RESPONSE_SIZE = 10 * 1024 * 1024

    # طبقه‌بندی اولیه بر اساس کدها و نمونه‌های مشاهده‌شده
    INSTRUMENT_TYPES = {
        "300": {
            "category": "سهام عادی",
            "is_common_stock": True,
            "status": "initial"
        },
        "303": {
            "category": "سهام عادی",
            "is_common_stock": True,
            "status": "initial"
        },
        "309": {
            "category": "سهام عادی",
            "is_common_stock": True,
            "status": "initial"
        },
        "313": {
            "category": "سهام عادی",
            "is_common_stock": True,
            "status": "initial"
        },

        "311": {
            "category": "اختیار خرید",
            "is_common_stock": False,
            "status": "initial"
        },
        "320": {
            "category": "اختیار خرید",
            "is_common_stock": False,
            "status": "initial"
        },
        "312": {
            "category": "اختیار فروش",
            "is_common_stock": False,
            "status": "initial"
        },
        "321": {
            "category": "اختیار فروش",
            "is_common_stock": False,
            "status": "initial"
        },

        "305": {
            "category": "صندوق سرمایه‌گذاری",
            "is_common_stock": False,
            "status": "initial"
        },
        "315": {
            "category": "صندوق سرمایه‌گذاری",
            "is_common_stock": False,
            "status": "initial"
        },
        "380": {
            "category": "صندوق کالایی",
            "is_common_stock": False,
            "status": "initial"
        },

        "306": {
            "category": "اوراق مرابحه",
            "is_common_stock": False,
            "status": "initial"
        },
        "706": {
            "category": "اوراق مرابحه دولتی",
            "is_common_stock": False,
            "status": "initial"
        },
        "208": {
            "category": "صکوک",
            "is_common_stock": False,
            "status": "initial"
        },
        "206": {
            "category": "اوراق و اسناد مالی",
            "is_common_stock": False,
            "status": "initial"
        },
        "301": {
            "category": "اوراق مشارکت",
            "is_common_stock": False,
            "status": "initial"
        },

        "304": {
            "category": "قرارداد آتی",
            "is_common_stock": False,
            "status": "initial"
        },
        "308": {
            "category": "سلف استاندارد",
            "is_common_stock": False,
            "status": "initial"
        },
        "200": {
            "category": "سلف موازی",
            "is_common_stock": False,
            "status": "initial"
        },

        "307": {
            "category": "امتیاز تسهیلات مسکن",
            "is_common_stock": False,
            "status": "initial"
        },
        "701": {
            "category": "گواهی کالایی",
            "is_common_stock": False,
            "status": "initial"
        },

        "400": {
            "category": "حق تقدم یا ابزار مرتبط",
            "is_common_stock": False,
            "status": "needs_review"
        },
        "403": {
            "category": "حق تقدم یا ابزار مرتبط",
            "is_common_stock": False,
            "status": "needs_review"
        },
        "404": {
            "category": "ابزار بیمه‌ای یا ناشناخته",
            "is_common_stock": False,
            "status": "needs_review"
        },

        "201": {
            "category": "گواهی ظرفیت",
            "is_common_stock": False,
            "status": "initial"
        },
        "210": {
            "category": "گواهی صرفه‌جویی انرژی",
            "is_common_stock": False,
            "status": "initial"
        },

        "801": {
            "category": "ابزار بازار برق",
            "is_common_stock": False,
            "status": "initial"
        },
        "802": {
            "category": "ابزار بازار برق",
            "is_common_stock": False,
            "status": "initial"
        },
        "803": {
            "category": "ابزار بازار برق",
            "is_common_stock": False,
            "status": "initial"
        },
        "804": {
            "category": "ابزار بازار برق",
            "is_common_stock": False,
            "status": "initial"
        }
    }

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
                except (
                    UnicodeDecodeError,
                    json.JSONDecodeError
                ):
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

    def classify_instrument(self, item):
        """تعیین گروه اولیه ابزار بر اساس yVal."""

        yval = str(item.get("yVal", "")).strip()

        instrument_type = self.INSTRUMENT_TYPES.get(yval)

        if instrument_type is None:
            return {
                "yVal": yval or "نامشخص",
                "flow": str(item.get("flow", "نامشخص")),
                "category": "سایر ابزارها - نیازمند بررسی",
                "is_common_stock": None,
                "classification_status": "unknown"
            }

        return {
            "yVal": yval,
            "flow": str(item.get("flow", "نامشخص")),
            "category": instrument_type["category"],
            "is_common_stock": instrument_type["is_common_stock"],
            "classification_status": instrument_type["status"]
        }

    def normalize_symbol(self, item):
        if not isinstance(item, dict):
            return None

        symbol = item.get("lVal18AFC") or item.get("lva")
        name = item.get("lVal30") or item.get("lvc")
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

        classification = self.classify_instrument(item)

        return {
            "instrument_code": code,
            "symbol": symbol,
            "name": name,
            **classification
        }

    def validate_symbols(self, data):
        rows = self.extract_rows(data)

        if not rows:
            return {
                "success": False,
                "error": "unexpected_data_structure",
                "message": "ساختار پاسخ API قابل شناسایی نیست."
            }

        first = rows[0]

        debug = {
            "first_row_type": type(first).__name__,
            "first_row_keys": (
                list(first.keys())[:50]
                if isinstance(first, dict)
                else []
            ),
            "first_row_sample": (
                {
                    str(k): str(v)[:80]
                    for k, v in list(first.items())[:12]
                }
                if isinstance(first, dict)
                else str(first)[:200]
            )
        }

        # گزارش تفصیلی بر اساس کد اصلی yVal
        classification_report = {}

        # گزارش تجمیعی بر اساس دسته‌بندی
        category_report = {}

        valid = []
        rejected = 0
        duplicates = 0
        seen = set()

        for item in rows:

            if isinstance(item, dict):
                yval = str(
                    item.get("yVal", "نامشخص")
                ).strip()

                flow = str(
                    item.get("flow", "نامشخص")
                ).strip()

                if yval not in classification_report:
                    classification_report[yval] = {
                        "count": 0,
                        "flow_counts": {},
                        "samples": []
                    }

                group = classification_report[yval]
                group["count"] += 1

                group["flow_counts"][flow] = (
                    group["flow_counts"].get(flow, 0) + 1
                )

                if len(group["samples"]) < 3:
                    group["samples"].append({
                        "symbol": item.get("lva"),
                        "name": item.get("lvc"),
                        "instrument_code": item.get("insCode")
                    })

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

            # ساخت گزارش گروهی از نمادهای معتبر
            category = normalized["category"]

            if category not in category_report:
                category_report[category] = {
                    "count": 0,
                    "yVal_codes": [],
                    "flow_counts": {},
                    "samples": []
                }

            category_group = category_report[category]
            category_group["count"] += 1

            if normalized["yVal"] not in category_group["yVal_codes"]:
                category_group["yVal_codes"].append(
                    normalized["yVal"]
                )

            flow = normalized["flow"]

            category_group["flow_counts"][flow] = (
                category_group["flow_counts"].get(flow, 0) + 1
            )

            if len(category_group["samples"]) < 3:
                category_group["samples"].append({
                    "symbol": normalized["symbol"],
                    "name": normalized["name"],
                    "instrument_code": code
                })

        # مرتب‌سازی گروه‌ها بر اساس تعداد
        category_report = dict(
            sorted(
                category_report.items(),
                key=lambda item: item[1]["count"],
                reverse=True
            )
        )

        # شمارش سهام عادی و ابزارهای ناشناخته
        common_stock_count = sum(
            1 for item in valid
            if item["is_common_stock"] is True
        )

        unknown_count = sum(
            1 for item in valid
            if item["classification_status"] == "unknown"
        )

        needs_review_count = sum(
            1 for item in valid
            if item["classification_status"] == "needs_review"
        )

        return {
            "success": True,
            "source": "TSETMC",

            "total_received": len(rows),
            "valid_count": len(valid),
            "rejected_count": rejected,
            "duplicate_count": duplicates,

            "common_stock_count": common_stock_count,
            "unknown_count": unknown_count,
            "needs_review_count": needs_review_count,

            "symbols": valid,

            "category_report": category_report,
            "classification_report": classification_report,

            "debug": debug,

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
    
