
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs
from datetime import datetime, timezone
import json
import mimetypes
import os
import sqlite3
import threading

from market_data.tsetmc import TSETMCClient
from market_data.symbols import SymbolManager
from market_data.history import HistoryManager


BASE = Path(__file__).resolve().parent
STATIC = (BASE / "static").resolve()
DATA = BASE / "data"
BACKUPS = DATA / "backups"
DB_PATH = DATA / "behzad_ai.sqlite3"

DATA.mkdir(exist_ok=True)
BACKUPS.mkdir(exist_ok=True)

DB_LOCK = threading.RLock()
MAX_BODY = 20000
MAX_MESSAGE = 4000
VERSION = "0.5.0"


def now_iso():
    return datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )


def connect_db():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with DB_LOCK, connect_db() as con:

        con.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL
                    CHECK(role IN ('user','assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # فهرست نمادهای دریافت‌شده از TSETMC
        con.execute("""
            CREATE TABLE IF NOT EXISTS market_symbols (
                instrument_code TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                yval TEXT,
                flow TEXT,
                category TEXT,
                is_common_stock INTEGER,
                classification_status TEXT,
                updated_at TEXT NOT NULL
            )
        """)

        # تاریخچه روزانه قیمت
        con.execute("""
            CREATE TABLE IF NOT EXISTS history_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument_code TEXT NOT NULL,
                trade_date TEXT NOT NULL,

                closing_price REAL,
                last_price REAL,
                min_price REAL,
                max_price REAL,
                yesterday_price REAL,
                first_price REAL,

                trade_count REAL,
                q_tot_tran_5j REAL,
                total_value REAL,

                raw_json TEXT,
                fetched_at TEXT NOT NULL,

                UNIQUE(instrument_code, trade_date),

                FOREIGN KEY(instrument_code)
                REFERENCES market_symbols(instrument_code)
            )
        """)

        con.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_history_code_date
            ON history_prices(
                instrument_code,
                trade_date
            )
        """)

        con.execute("PRAGMA journal_mode=WAL")
        con.commit()


def save_message(role, content):
    with DB_LOCK, connect_db() as con:
        con.execute(
            """
            INSERT INTO messages(role, content, created_at)
            VALUES(?,?,?)
            """,
            (role, content, now_iso())
        )
        con.commit()


def save_symbols(symbols):
    """ذخیره یا به‌روزرسانی فهرست ابزارهای بازار."""

    stamp = now_iso()

    with DB_LOCK, connect_db() as con:

        for item in symbols:

            is_common = item.get("is_common_stock")

            if is_common is True:
                is_common = 1
            elif is_common is False:
                is_common = 0
            else:
                is_common = None

            con.execute("""
                INSERT INTO market_symbols (
                    instrument_code,
                    symbol,
                    name,
                    yval,
                    flow,
                    category,
                    is_common_stock,
                    classification_status,
                    updated_at
                )
                VALUES (?,?,?,?,?,?,?,?,?)

                ON CONFLICT(instrument_code)
                DO UPDATE SET
                    symbol=excluded.symbol,
                    name=excluded.name,
                    yval=excluded.yval,
                    flow=excluded.flow,
                    category=excluded.category,
                    is_common_stock=excluded.is_common_stock,
                    classification_status=
                        excluded.classification_status,
                    updated_at=excluded.updated_at
            """, (
                item.get("instrument_code"),
                item.get("symbol"),
                item.get("name"),
                item.get("yVal"),
                item.get("flow"),
                item.get("category"),
                is_common,
                item.get("classification_status"),
                stamp
            ))

        con.commit()


def save_history_records(ins_code, records):
    """ذخیره تاریخچه با جلوگیری از ثبت رکورد تکراری."""

    inserted = 0
    updated = 0

    with DB_LOCK, connect_db() as con:

        for item in records:

            cursor = con.execute("""
                INSERT INTO history_prices (
                    instrument_code,
                    trade_date,
                    closing_price,
                    last_price,
                    min_price,
                    max_price,
                    yesterday_price,
                    first_price,
                    trade_count,
                    q_tot_tran_5j,
                    total_value,
                    raw_json,
                    fetched_at
                )
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)

                ON CONFLICT(instrument_code, trade_date)
                DO UPDATE SET
                    closing_price=excluded.closing_price,
                    last_price=excluded.last_price,
                    min_price=excluded.min_price,
                    max_price=excluded.max_price,
                    yesterday_price=excluded.yesterday_price,
                    first_price=excluded.first_price,
                    trade_count=excluded.trade_count,
                    q_tot_tran_5j=excluded.q_tot_tran_5j,
                    total_value=excluded.total_value,
                    raw_json=excluded.raw_json,
                    fetched_at=excluded.fetched_at
            """, (
                ins_code,
                item["trade_date"],
                item.get("closing_price"),
                item.get("last_price"),
                item.get("min_price"),
                item.get("max_price"),
                item.get("yesterday_price"),
                item.get("first_price"),
                item.get("trade_count"),
                item.get("q_tot_tran_5j"),
                item.get("total_value"),
                item.get("raw_json"),
                now_iso()
            ))

            if cursor.rowcount:
                # SQLite در UPSERT مقدار rowcount را 1 برمی‌گرداند.
                # برای آمار دقیق، بعداً از تعداد کل رکوردها استفاده می‌کنیم.
                inserted += 1

        con.commit()

    return inserted


def make_backup():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUPS / f"behzad_ai_backup_{stamp}.sqlite3"

    with DB_LOCK:
        source = connect_db()

        try:
            dest = sqlite3.connect(target)
            source.backup(dest)
            dest.close()
        finally:
            source.close()

    return target


def json_bytes(payload):
    return json.dumps(
        payload,
        ensure_ascii=False
    ).encode("utf-8")


class Handler(BaseHTTPRequestHandler):

    def send_data(
        self,
        code,
        data,
        kind="application/json; charset=utf-8"
    ):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, code, payload):
        self.send_data(code, json_bytes(payload))

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))

        if not 1 <= length <= MAX_BODY:
            raise ValueError("invalid body size")

        return json.loads(
            self.rfile.read(length).decode("utf-8")
        )

    def do_GET(self):

        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)

        # دریافت و ذخیره فهرست نمادهای بازار
        if path == "/api/market/symbols":

            result = SymbolManager(
                timeout=25
            ).get_symbols()

            if not result.get("success"):
                return self.send_json(502, {
                    "ok": False,
                    "market_source": "TSETMC",
                    "result": result
                })

            symbols = result.get("symbols", [])

            save_symbols(symbols)

            return self.send_json(200, {
                "ok": True,
                "market_source": "TSETMC",

                "total_received": result.get(
                    "total_received", 0
                ),
                "valid_count": result.get(
                    "valid_count", 0
                ),
                "rejected_count": result.get(
                    "rejected_count", 0
                ),
                "duplicate_count": result.get(
                    "duplicate_count", 0
                ),

                "common_stock_count": result.get(
                    "common_stock_count", 0
                ),
                "unknown_count": result.get(
                    "unknown_count", 0
                ),
                "needs_review_count": result.get(
                    "needs_review_count", 0
                ),

                "classification_total": result.get(
                    "classification_total", 0
                ),
                "category_total": result.get(
                    "category_total", 0
                ),
                "reports_consistent": result.get(
                    "reports_consistent", False
                ),

                "category_report": result.get(
                    "category_report", {}
                ),
                "classification_report": result.get(
                    "classification_report", {}
                ),

                "preview": symbols[:10],
                "debug": result.get("debug"),
                "checked_at": result.get("checked_at")
            })

        # بررسی ارتباط با TSETMC
        if path == "/api/market/connection":

            result = TSETMCClient(
                timeout=15
            ).check_connection()

            return self.send_json(
                200 if result["success"] else 502,
                {
                    "ok": result["success"],
                    "market_source": "TSETMC",
                    "connection": result
                }
            )

        # وضعیت موتور تاریخچه
        if path == "/api/market/history/status":

            with DB_LOCK, connect_db() as con:

                symbol_count = con.execute("""
                    SELECT COUNT(*)
                    FROM market_symbols
                    WHERE is_common_stock = 1
                """).fetchone()[0]

                history_symbols = con.execute("""
                    SELECT COUNT(DISTINCT instrument_code)
                    FROM history_prices
                """).fetchone()[0]

                history_count = con.execute("""
                    SELECT COUNT(*)
                    FROM history_prices
                """).fetchone()[0]

                latest = con.execute("""
                    SELECT MAX(trade_date)
                    FROM history_prices
                """).fetchone()[0]

            return self.send_json(200, {
                "ok": True,
                "common_stock_symbols": symbol_count,
                "symbols_with_history": history_symbols,
                "total_history_records": history_count,
                "latest_trade_date": latest,
                "storage": "sqlite"
            })

        # مشاهده تاریخچه قیمت یک نماد
        if path == "/api/history/prices":

            ins_code = str(
                query.get("ins_code", [""])[0]
            ).strip()

            if not ins_code.isdigit():
                return self.send_json(400, {
                    "ok": False,
                    "error": "کد نماد نامعتبر است."
                })

            try:
                limit = int(
                    query.get("limit", ["500"])[0]
                )
            except ValueError:
                limit = 500

            limit = max(1, min(limit, 5000))

            with DB_LOCK, connect_db() as con:

                symbol = con.execute("""
                    SELECT symbol, name, category
                    FROM market_symbols
                    WHERE instrument_code = ?
                """, (ins_code,)).fetchone()

                rows = con.execute("""
                    SELECT
                        trade_date,
                        closing_price,
                        last_price,
                        min_price,
                        max_price,
                        yesterday_price,
                        first_price,
                        trade_count,
                        q_tot_tran_5j,
                        total_value,
                        fetched_at
                    FROM history_prices
                    WHERE instrument_code = ?
                    ORDER BY trade_date DESC
                    LIMIT ?
                """, (ins_code, limit)).fetchall()

            return self.send_json(200, {
                "ok": True,
                "instrument_code": ins_code,
                "symbol": dict(symbol) if symbol else None,
                "count": len(rows),
                "records": [dict(row) for row in rows]
            })

        # سلامت سامانه
        if path == "/api/health":

            with DB_LOCK, connect_db() as con:

                count = con.execute(
                    "SELECT COUNT(*) FROM messages"
                ).fetchone()[0]

                price_count = con.execute(
                    "SELECT COUNT(*) FROM history_prices"
                ).fetchone()[0]

            return self.send_json(200, {
                "status": "ok",
                "app": "BEHZAD AI",
                "version": VERSION,
                "storage": "sqlite",
                "saved_messages": count,
                "saved_price_records": price_count
            })

        # تاریخچه پیام‌ها
        if path == "/api/history":

            with DB_LOCK, connect_db() as con:
                rows = con.execute("""
                    SELECT id, role, content, created_at
                    FROM messages
                    ORDER BY id ASC
                """).fetchall()

            return self.send_json(200, {
                "ok": True,
                "messages": [dict(row) for row in rows]
            })

        # تنظیمات
        if path == "/api/settings":

            with DB_LOCK, connect_db() as con:
                rows = con.execute(
                    "SELECT key, value FROM settings"
                ).fetchall()

            return self.send_json(200, {
                "ok": True,
                "settings": {
                    row["key"]: row["value"]
                    for row in rows
                }
            })

        # فهرست پشتیبان‌ها
        if path == "/api/backups":

            items = []

            for p in sorted(
                BACKUPS.glob("*.sqlite3"),
                reverse=True
            ):
                items.append({
                    "name": p.name,
                    "size": p.stat().st_size
                })

            return self.send_json(200, {
                "ok": True,
                "backups": items
            })

        # فایل‌های رابط کاربری
        relative = (
            "index.html"
            if path == "/"
            else path[len("/static/"):]
            if path.startswith("/static/")
            else None
        )

        if relative is None:
            return self.send_error(404)

        target = (STATIC / relative).resolve()

        if (
            not target.is_relative_to(STATIC)
            or not target.is_file()
        ):
            return self.send_error(404)

        data = target.read_bytes()

        kind = (
            mimetypes.guess_type(str(target))[0]
            or "application/octet-stream"
        )

        if kind.startswith("text/") or kind in (
            "application/javascript",
            "application/json"
        ):
            kind += "; charset=utf-8"

        return self.send_data(200, data, kind)

    def do_POST(self):

        path = urlparse(self.path).path

        try:
            payload = self.read_json()

            # دریافت و ذخیره تاریخچه یک نماد
            if path == "/api/market/history/fetch":

                ins_code = str(
                    payload.get("ins_code", "")
                ).strip()

                if (
                    not ins_code.isdigit()
                    or not 5 <= len(ins_code) <= 25
                ):
                    return self.send_json(400, {
                        "ok": False,
                        "error": "کد شناسایی نماد نامعتبر است."
                    })

                # نماد باید قبلاً از فهرست بازار دریافت شده باشد.
                with DB_LOCK, connect_db() as con:

                    symbol = con.execute("""
                        SELECT *
                        FROM market_symbols
                        WHERE instrument_code = ?
                    """, (ins_code,)).fetchone()

                if symbol is None:
                    return self.send_json(404, {
                        "ok": False,
                        "error": (
                            "نماد در فهرست ذخیره‌شده وجود ندارد. "
                            "ابتدا فهرست نمادهای بازار را دریافت کنید."
                        )
                    })

                if symbol["is_common_stock"] != 1:
                    return self.send_json(409, {
                        "ok": False,
                        "error": (
                            "این ابزار در طبقه سهام عادی "
                            "قرار ندارد."
                        ),
                        "category": symbol["category"]
                    })

                result = HistoryManager(
                    timeout=30
                ).fetch(ins_code)

                if not result.get("success"):
                    return self.send_json(502, {
                        "ok": False,
                        "market_source": "TSETMC",
                        "error": result.get("error"),
                        "ins_code": ins_code
                    })

                records = result.get("records", [])

                save_history_records(
                    ins_code,
                    records
                )

                with DB_LOCK, connect_db() as con:
                    total = con.execute("""
                        SELECT COUNT(*)
                        FROM history_prices
                        WHERE instrument_code = ?
                    """, (ins_code,)).fetchone()[0]

                    latest = con.execute("""
                        SELECT MAX(trade_date)
                        FROM history_prices
                        WHERE instrument_code = ?
                    """, (ins_code,)).fetchone()[0]

                return self.send_json(200, 
