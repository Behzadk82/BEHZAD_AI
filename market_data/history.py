
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone


class HistoryManager:
    """دریافت و اعتبارسنجی تاریخچه روزانه قیمت از TSETMC."""

    BASE_URL = (
        "https://cdn.tsetmc.com/api/"
        "ClosingPrice/GetClosingPriceDailyList"
    )

    MAX_RESPONSE_SIZE = 8 * 1024 * 1024

    def __init__(self, timeout=25):
        self.timeout = timeout

    @staticmethod
    def now_iso():
        return datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        )

    @staticmethod
    def to_number(value):
        if value is None or value == "":
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def valid_ins_code(ins_code):
        value = str(ins_code or "").strip()
        return value.isdigit() and 5 <= len(value) <= 25

    @staticmethod
    def normalize_date(value):
        text = str(value or "").strip()

        if len(text) != 8 or not text.isdigit():
            return None

        try:
            datetime.strptime(text, "%Y%m%d")
            return text
        except ValueError:
            return None

    def fetch(self, ins_code):
        ins_code = str(ins_code or "").strip()

        if not self.valid_ins_code(ins_code):
            return {
                "success": False,
                "error": "کد نماد نامعتبر است."
            }

        url = f"{self.BASE_URL}/{ins_code}/0"

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/120.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.tsetmc.com/",
                "Origin": "https://www.tsetmc.com"
            }
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout
            ) as response:

                raw = response.read(
                    self.MAX_RESPONSE_SIZE + 1
                )

            if len(raw) > self.MAX_RESPONSE_SIZE:
                return {
                    "success": False,
                    "error": "حجم پاسخ بیش از حد مجاز است."
                }

            payload = json.loads(
                raw.decode("utf-8")
            )

            records = payload.get("closingPriceDaily", [])

            if not isinstance(records, list):
                return {
                    "success": False,
                    "error": "ساختار تاریخچه نامعتبر است."
                }

            rows = []
            rejected = 0

            for item in records:
                if not isinstance(item, dict):
                    rejected += 1
                    continue

                trade_date = self.normalize_date(
                    item.get("dEven")
                )

                if not trade_date:
                    rejected += 1
                    continue

                rows.append({
                    "ins_code": ins_code,
                    "trade_date": trade_date,
                    "closing_price": self.to_number(
                        item.get("pClosing")
                    ),
                    "last_price": self.to_number(
                        item.get("pDrCotVal")
                    ),
                    "min_price": self.to_number(
                        item.get("priceMin")
                    ),
                    "max_price": self.to_number(
                        item.get("priceMax")
                    ),
                    "yesterday_price": self.to_number(
                        item.get("priceYesterday")
                    ),
                    "first_price": self.to_number(
                        item.get("priceFirst")
                    ),
                    "trade_count": self.to_number(
                        item.get("zTotTran")
                    ),
                    "q_tot_tran_5j": self.to_number(
                        item.get("qTotTran5J")
                    ),
                    "total_value": self.to_number(
                        item.get("qTotCap")
                    ),
                    "raw_json": json.dumps(
                        item,
                        ensure_ascii=False
                    )
                })

            # حذف تاریخ‌های تکراری در پاسخ
            unique = {}

            for row in rows:
                unique[row["trade_date"]] = row

            clean_rows = sorted(
                unique.values(),
                key=lambda x: x["trade_date"]
            )

            return {
                "success": True,
                "ins_code": ins_code,
                "count": len(clean_rows),
                "rejected_count": rejected,
                "records": clean_rows,
                "fetched_at": self.now_iso()
            }

        except urllib.error.HTTPError as exc:
            return {
                "success": False,
                "error": f"خطای HTTP از TSETMC: {exc.code}"
            }

        except urllib.error.URLError as exc:
            return {
                "success": False,
                "error": f"ارتباط با TSETMC برقرار نشد: {exc.reason}"
            }

        except TimeoutError:
            return {
                "success": False,
                "error": "زمان دریافت تاریخچه به پایان رسید."
            }

        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "پاسخ TSETMC فرمت JSON معتبر ندارد."
            }

        except Exception as exc:
            return {
                "success": False,
                "error": f"خطای پیش‌بینی‌نشده: {str(exc)[:250]}"
          }
              
