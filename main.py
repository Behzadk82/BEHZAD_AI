from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote
from datetime import datetime, timezone
import json
import mimetypes
import os
import shutil
import sqlite3
import threading
import zipfile

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
VERSION = "0.4.0"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect_db():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with DB_LOCK, connect_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL CHECK(role IN ('user','assistant')),
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
        con.execute("PRAGMA journal_mode=WAL")
        con.commit()


def save_message(role, content):
    with DB_LOCK, connect_db() as con:
        con.execute(
            "INSERT INTO messages(role, content, created_at) VALUES(?,?,?)",
            (role, content, now_iso())
        )
        con.commit()


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
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def send_data(self, code, data, kind="application/json; charset=utf-8"):
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
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        path = unquote(urlparse(self.path).path)

        if path == "/api/health":
            with DB_LOCK, connect_db() as con:
                count = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            return self.send_json(200, {
                "status": "ok", "app": "BEHZAD AI", "version": VERSION,
                "storage": "sqlite", "saved_messages": count
            })

        if path == "/api/history":
            with DB_LOCK, connect_db() as con:
                rows = con.execute(
                    "SELECT id, role, content, created_at FROM messages ORDER BY id ASC"
                ).fetchall()
            return self.send_json(200, {"ok": True, "messages": [dict(r) for r in rows]})

        if path == "/api/settings":
            with DB_LOCK, connect_db() as con:
                rows = con.execute("SELECT key, value FROM settings").fetchall()
            return self.send_json(200, {"ok": True, "settings": {r["key"]: r["value"] for r in rows}})

        if path == "/api/backups":
            items = []
            for p in sorted(BACKUPS.glob("*.sqlite3"), reverse=True):
                items.append({"name": p.name, "size": p.stat().st_size})
            return self.send_json(200, {"ok": True, "backups": items})

        relative = "index.html" if path == "/" else path[len("/static/"):] if path.startswith("/static/") else None
        if relative is None:
            return self.send_error(404)
        target = (STATIC / relative).resolve()
        if not target.is_relative_to(STATIC) or not target.is_file():
            return self.send_error(404)
        data = target.read_bytes()
        kind = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if kind.startswith("text/") or kind in ("application/javascript", "application/json"):
            kind += "; charset=utf-8"
        return self.send_data(200, data, kind)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self.read_json()

            if path == "/api/chat":
                message = str(payload.get("message", "")).strip()
                if not message or len(message) > MAX_MESSAGE:
                    return self.send_json(400, {"ok": False, "error": "متن پیام نامعتبر است."})
                save_message("user", message)
                reply = (
                    "پیام شما با موفقیت در سرور BEHZAD AI دریافت و ذخیره شد.\n\n"
                    "این پاسخ هنوز آزمایشی است و از مدل هوش مصنوعی زنده تولید نشده است."
                )
                save_message("assistant", reply)
                return self.send_json(200, {"ok": True, "mode": "local-test", "reply": reply})

            if path == "/api/backup":
                target = make_backup()
                return self.send_json(200, {"ok": True, "name": target.name, "size": target.stat().st_size})

            if path == "/api/restore":
                name = str(payload.get("name", ""))
                if not name or Path(name).name != name or not name.endswith(".sqlite3"):
                    return self.send_json(400, {"ok": False, "error": "نام فایل پشتیبان نامعتبر است."})
                source = (BACKUPS / name).resolve()
                if not source.is_relative_to(BACKUPS.resolve()) or not source.is_file():
                    return self.send_json(404, {"ok": False, "error": "فایل پشتیبان پیدا نشد."})
                # Keep a safety copy before replacing the live database.
                make_backup()
                check = sqlite3.connect(source)
                try:
                    result = check.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('messages','settings')"
                    ).fetchall()
                    tables = {r[0] for r in result}
                    if not {"messages", "settings"}.issubset(tables):
                        return self.send_json(400, {"ok": False, "error": "ساختار فایل پشتیبان معتبر نیست."})
                finally:
                    check.close()
                with DB_LOCK:
                    live = connect_db()
                    backup_db = sqlite3.connect(source)
                    try:
                        backup_db.backup(live)
                    finally:
                        backup_db.close()
                        live.close()
                return self.send_json(200, {"ok": True, "message": "بازیابی اطلاعات انجام شد."})

            if path == "/api/settings":
                note = str(payload.get("project_note", ""))
                if len(note) > 5000:
                    return self.send_json(400, {"ok": False, "error": "یادداشت بیش از حد طولانی است."})
                with DB_LOCK, connect_db() as con:
                    con.execute(
                        "INSERT INTO settings(key,value,updated_at) VALUES('project_note',?,?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                        (note, now_iso())
                    )
                    con.commit()
                return self.send_json(200, {"ok": True, "saved_at": now_iso()})

            return self.send_error(404)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return self.send_json(400, {"ok": False, "error": "درخواست نامعتبر است."})
        except sqlite3.Error:
            return self.send_json(500, {"ok": False, "error": "خطا در ذخیره‌سازی پایگاه داده."})

    def log_message(self, fmt, *args):
        print("[BEHZAD_AI]", fmt % args)


init_db()
# A backup is made on startup if there is already project data.
if DB_PATH.exists() and DB_PATH.stat().st_size > 0:
    try:
        make_backup()
    except sqlite3.Error:
        pass

host = os.environ.get("HOST", "127.0.0.1")
port = int(os.environ.get("PORT", "8000"))
server = ThreadingHTTPServer((host, port), Handler)
print(f"BEHZAD AI v{VERSION} SERVER STARTED")
print(f"Open: http://{host}:{port}")
server.serve_forever()
