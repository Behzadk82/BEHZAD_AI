# src/api/dashboard_server.py
# Simple static file server for the dashboard.
# Serves files from /dashboard on http://127.0.0.1:8001

import os
import mimetypes
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import BASE_DIR


DASHBOARD_DIR = BASE_DIR / "dashboard"
HOST = "127.0.0.1"
PORT = 8001


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def end_headers(self):
        # CORS headers for API calls from browser
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        print(f"[DASH] {fmt % args}")


def main():
    if not DASHBOARD_DIR.exists():
        print(f"[ERROR] Dashboard not found: {DASHBOARD_DIR}")
        return
    print("=" * 60)
    print("BEHZAD_AI DASHBOARD")
    print(f"Listening on http://{HOST}:{PORT}")
    print(f"Serving: {DASHBOARD_DIR}")
    print("=" * 60)
    print()
    print("⚠️  مهم: API باید روی پورت 8000 در حال اجرا باشد!")
    print("   (در ترمینال دیگر: python src/api/server.py)")
    print()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[STOP] Dashboard stopped.")


if __name__ == "__main__":
    main()
