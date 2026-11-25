# run_all.py
import json, sqlite3
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from src.config import DB_PATH
from src.analysis.deep_analyzer import DeepAnalyzer

DASHBOARD_DIR = BASE / "dashboard"
HOST, PORT = "0.0.0.0", 8000
VERSION = "0.8.0"

def get_db():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    return con

class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, ctype):
        if not path.exists(): return self._send_json(404, {"error": "Not found"})
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/" or path == "/dashboard": return self._send_file(DASHBOARD_DIR / "index.html", "text/html")
        if path == "/style.css": return self._send_file(DASHBOARD_DIR / "style.css", "text/css")
        if path == "/app.js": return self._send_file(DASHBOARD_DIR / "app.js", "application/javascript")

        try:
            if path == "/api/health": return self._send_json(200, {"status": "ok", "version": VERSION})
            if path == "/api/smart-scan":
                analyzer = DeepAnalyzer()
                try:
                    results = analyzer.scan_all(min_score=40)
                    return self._send_json(200, {"count": len(results), "items": results})
                finally:
                    analyzer.close()
            return self._send_json(404, {"error": "Not found"})
        except Exception as e:
            return self._send_json(500, {"error": str(e)})

    def log_message(self, fmt, *args): pass

if __name__ == "__main__":
    if not DB_PATH.exists(): raise SystemExit(f"DB not found: {DB_PATH}")
    print(f"BEHZAD_AI v{VERSION} - Deep Analyzer active")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
