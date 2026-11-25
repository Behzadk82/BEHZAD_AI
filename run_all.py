# run_all.py
# Combined server: API + Dashboard in one place.
# Just run: python run_all.py
# Then open: http://127.0.0.1:8000

import json
import sqlite3
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from src.config import DB_PATH

DASHBOARD_DIR = BASE / "dashboard"
HOST = "0.0.0.0"  # listen on all interfaces
PORT = 8000
VERSION = "0.5.0"


def get_db():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    return con


def rows_to_list(rows):
    return [dict(r) for r in rows]


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        if not path.exists():
            return self._send_json(404, {"error": "Not found"})
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)

        # --- Static files ---
        if path == "/" or path == "/dashboard":
            return self._send_file(DASHBOARD_DIR / "index.html", "text/html")
        if path == "/style.css":
            return self._send_file(DASHBOARD_DIR / "style.css", "text/css")
        if path == "/app.js":
            return self._send_file(DASHBOARD_DIR / "app.js", "application/javascript")

        # --- API routes ---
        try:
            if path == "/api/symbols":
                limit = int(query.get("limit", ["50"])[0])
                offset = int(query.get("offset", ["0"])[0])
                search = query.get("search", [None])[0]
                con = get_db()
                try:
                    if search:
                        pattern = f"%{search}%"
                        rows = con.execute(
                            "SELECT * FROM symbols WHERE symbol LIKE ? OR name LIKE ? "
                            "ORDER BY trades DESC LIMIT ? OFFSET ?",
                            (pattern, pattern, limit, offset),
                        ).fetchall()
                        total = con.execute(
                            "SELECT COUNT(*) FROM symbols WHERE symbol LIKE ? OR name LIKE ?",
                            (pattern, pattern),
                        ).fetchone()[0]
                    else:
                        rows = con.execute(
                            "SELECT * FROM symbols ORDER BY trades DESC LIMIT ? OFFSET ?",
                            (limit, offset),
                        ).fetchall()
                        total = con.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
                    return self._send_json(200, {"total": total, "limit": limit, "offset": offset, "items": rows_to_list(rows)})
                finally:
                    con.close()

            parts = [p for p in path.split("/") if p]

            if len(parts) == 3 and parts[0] == "api" and parts[1] == "latest":
                ins_code = parts[2]
                con = get_db()
                try:
                    symbol = con.execute(
                        "SELECT symbol, name, last_price, volume, trades FROM symbols WHERE ins_code = ?",
                        (ins_code,),
                    ).fetchone()
                    if not symbol:
                        return self._send_json(404, {"error": "Symbol not found"})
                    price = con.execute(
                        "SELECT * FROM price_history WHERE ins_code = ? ORDER BY date DESC LIMIT 1",
                        (ins_code,),
                    ).fetchone()
                    ind = con.execute(
                        "SELECT * FROM indicators WHERE ins_code = ? ORDER BY date DESC LIMIT 1",
                        (ins_code,),
                    ).fetchone()
                    return self._send_json(200, {
                        "symbol": dict(symbol),
                        "latest_price": dict(price) if price else None,
                        "latest_indicators": dict(ind) if ind else None,
                    })
                finally:
                    con.close()

            if len(parts) == 3 and parts[0] == "api" and parts[1] == "history":
                ins_code = parts[2]
                limit = int(query.get("limit", ["100"])[0])
                con = get_db()
                try:
                    rows = con.execute(
                        "SELECT * FROM price_history WHERE ins_code = ? ORDER BY date DESC LIMIT ?",
                        (ins_code, limit),
                    ).fetchall()
                    return self._send_json(200, {"ins_code": ins_code, "items": rows_to_list(rows)})
                finally:
                    con.close()

            if len(parts) == 3 and parts[0] == "api" and parts[1] == "indicators":
                ins_code = parts[2]
                limit = int(query.get("limit", ["100"])[0])
                con = get_db()
                try:
                    rows = con.execute(
                        "SELECT * FROM indicators WHERE ins_code = ? ORDER BY date DESC LIMIT ?",
                        (ins_code, limit),
                    ).fetchall()
                    return self._send_json(200, {"ins_code": ins_code, "items": rows_to_list(rows)})
                finally:
                    con.close()

            if path == "/api/health":
                return self._send_json(200, {"status": "ok", "version": VERSION})

            return self._send_json(404, {"error": "Not found", "path": path})

        except Exception as e:
            return self._send_json(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        print(f"[SRV] {fmt % args}")


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"[ERROR] DB not found: {DB_PATH}")
        raise SystemExit(1)
    
    print("=" * 60)
    print(f"BEHZAD_AI SERVER v{VERSION}")
    print(f"Listening on http://0.0.0.0:{PORT}")
    print("=" * 60)
    print()
    print("📱 Open in browser:")
    print(f"   http://127.0.0.1:{PORT}")
    print()
    print("⛔ Press Ctrl+C to stop")
    print()
    
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[STOP] Server stopped.")
