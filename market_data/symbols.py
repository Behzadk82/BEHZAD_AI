
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

    # طبقه‌بندی اولیه؛ نیازمند تطبیق نهایی با اطلاعات رسمی ابزارها
    INSTRUMENT_TYPES = {
        "300": ("سهام عادی", True, "initial"),
        "303": ("سهام عادی", True, "initial"),
        "309": ("سهام عادی", True, "initial"),
        "313": ("سهام عادی", True, "initial"),

        "311": ("اختیار خرید", False, "initial"),
        "320": ("اختیار خرید", False, "initial"),
        "312": ("اختیار فروش", False, "initial"),
        "321": ("اختیار فروش", False, "initial"),

        "305": ("صندوق سرمایه‌گذاری", False, "initial"),
        "315": ("صندوق سرمایه‌گذاری", False, "initial"),
        "380": ("صندوق کالایی", False, "initial"),

        "306": ("اوراق مرابحه", False, "initial"),
        "706": ("اوراق مرابحه دولتی", False, "initial"),
        "208": ("صکوک", False, "initial"),
        "206": ("اوراق و اسناد مالی", False, "initial"),
        "301": ("اوراق مشارکت", False, "initial"),

        "304": ("قرارداد آتی", False, "initial"),
        "308": ("سلف استاندارد", False, "initial"),
        "200": ("سلف موازی", False, "initial"),

        "307": ("امتیاز تسهیلات مسکن", False, "initial"),
        "701": ("گواهی کالایی", False, "initial"),

        "400": ("حق تقدم یا ابزار مرتبط", False, "needs_review"),
        "403": ("حق تقدم یا ابزار مرتبط", False, "needs_review"),
        "404": ("ابزار بیمه‌ای یا ناشناخته", False, "needs_review"),

        "201": ("گواهی ظرفیت", False, "initial"),
        "210": ("گواهی صرفه‌جویی انرژی", False, "initial"),

        "801": ("ابزار بازار برق", False, "initial"),
        "802": ("ابزار بازار برق", False, "initial"),
        "803": ("ابزار بازار برق", False, "initial"),
        "804": ("ابزار بازار برق", False, "initial"),
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

        category, is_common_stock, status = instrument_type

        return {
            "yVal": yval,
            "flow": str(item.get("flow", "نامشخص")),
            "category": category,
            "is_common_stock": is_common_stock,
            "classification_status": status
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

    @staticmethod
    def add_report_entry(report, key, normalized):
        """افزودن یک نماد معتبر به گزارش."""

        if key not in report:
            report[key] = {
                "count": 0,
                "flow_counts": {},
                "samples": []
            }

        group = report[key]
        group["count"] += 1

        flow = normalized["flow"]
        group["flow_counts"][flow] = (
            group["flow_counts"].get(flow, 0) + 1
        )

        if len(group["samples"]) < 3:
            group["samples"].append({
                "symbol": normalized["symbol"],
                "name": normalized["name"],
                "instrument_code": normalized["instrument_code"]
            })

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

        valid = []
        rejected = 0
        duplicates = 0
        seen = set()

        # هر دو گزارش فقط از نمادهای معتبر و یکتا ساخته می‌شوند.
        classification_report = {}
        category_report = {}

        for item in rows:

            normalized = self.normalize_symbol(item)

            if normalized is None:
                rejected += 1
                continue

            code = normalized["instrument_code"]

            # حذف شناسه‌های تکراری
            if code in seen:
                duplicates += 1
                continue

            seen.add(code)
            valid.append(normalized)

            # گزارش بر اساس کد اصلی yVal
            yval = normalized["yVal"]

            self.add_report_entry(
                classification_report,
                yval,
                normalized
            )

            # گزارش بر اساس گروه ابزار
            category = normalized["category"]

            self.add_report_entry(
                category_report,
                category,
                normalized
            )

            # ثبت کدهای yVal در گزارش گروهی
            category_group = category_report[category]

            if "yVal_codes" not in category_group:
                category_group["yVal_codes"] = []

            if yval not in category_group["yVal_codes"]:
                category_group["yVal_codes"].append(yval)

        # مرتب‌سازی گزارش‌ها بر اساس تعداد
        classification_report = dict(
            sorted(
                classification_report.items(),
                key=lambda item: item[1]["count"],
                reverse=True
            )
        )

        category_report = dict(
            sorted(
                category_report.items(),
                key=lambda item: item[1]["count"],
                reverse=True
            )
        )

        # شمارش وضعیت طبقه‌بندی
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

        # کنترل صحت مجموع گزارش‌ها
        classification_total = sum(
            group["count"]
            for group in classification_report.values()
        )

        category_total = sum(
            group["count"]
            for group in category_report.values()
        )

        reports_consistent = (
            classification_total == len(valid)
            and category_total == len(valid)
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

            "classification_total": classification_total,
            "category_total": category_total,
            "reports_consistent": reports_consistent,

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
            
