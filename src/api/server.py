# src/api/server.py
# BEHZAD_AI REST API - Phase 2.3
# Pure Python stdlib (no FastAPI needed) - works on any Python.

import json
import sqlite3
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH


VERSION = "0.3.0"
HOST = "127.0.0.1"
PORT = 8000


# ---------- DB ----------
def get_db():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    return con


def rows_to_list(rows):
    return [dict(r) for r in rows]


# ---------- Handlers ----------
def api_root():
    return {
        "app": "BEHZAD_AI",
        "version": VERSION,
        "endpoints": [
            "/api/symbols",
            "/api/symbols/{ins_code}",
            "/api/history/{ins_code}",
            "/api/indicators/{ins_code}",
            "/api/latest/{ins_code}",
        ],
    }


def api_symbols(query):
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
        return {"total": total, "limit": limit, "offset": offset, "items": rows_to_list(rows)}
    finally:
        con.close()


def api_symbol(ins_code):
    con = get_db()
    try:
        row = con.execute("SELECT * FROM symbols WHERE ins_code = ?", (ins_code,)).fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        con.close()


def api_history(ins_code, query):
    limit = int(query.get("limit", ["100"])[0])
    offset = int(query.get("offset", ["0"])[0])
    from_date = query.get("from_date", [None])[0]
    to_date = query.get("to_date", [None])[0]
    
    con = get_db()
    try:
        where = ["ins_code = ?"]
        params = [ins_code]
        if from_date:
            where.append("date >= ?")
            params.append(int(from_date))
        if to_date:
            where.append("date <= ?")
            params.append(int(to_date))
        
        where_sql = " AND ".join(where)
        rows = con.execute(
            f"SELECT * FROM price_history WHERE {where_sql} "
            f"ORDER BY date DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
        total = con.execute(
            f"SELECT COUNT(*) FROM price_history WHERE {where_sql}", params
        ).fetchone()[0]
        return {"ins_code": ins_code, "total": total, "limit": limit, "offset": offset, "items": rows_to_list(rows)}
    finally:
        con.close()


def api_indicators(ins_code, query):
    limit = int(query.get("limit", ["100"])[0])
    offset = int(query.get("offset", ["0"])[0])
    
    con = get_db()
    try:
        rows = con.execute(
            "SELECT * FROM indicators WHERE ins_code = ? "
            "ORDER BY date DESC LIMIT ? OFFSET ?",
            (ins_code, limit, offset),
        ).fetchall()
        total = con.execute(
            "SELECT COUNT(*) FROM indicators WHERE ins_code = ?", (ins_code,)
        ).fetchone()[0]
        return {"ins_code": ins_code, "total": total, "limit": limit, "offset": offset, "items": rows_to_list(rows)}
    finally:
        con.close()


def api_latest(ins_code):
    con = get_db()
    try:
        symbol = con.execute(
            "SELECT symbol, name, last_price, volume, trades FROM symbols WHERE ins_code = ?",
            (ins_code,),
        ).fetchone()
        if not symbol:
            return None
        price = con.execute(
            "SELECT * FROM price_history WHERE ins_code = ? ORDER BY date DESC LIMIT 1",
            (ins_code,),
        ).fetchone()
        ind = con.execute(
            "SELECT * FROM indicators WHERE ins_code = ? ORDER BY date DESC LIMIT 1",
            (ins_code,),
        ).fetchone()
        return {
            "symbol": dict(symbol),
            "latest_price": dict(price) if price else None,
            "latest_indicators": dict(ind) if ind else None,
        }
    finally:
        con.close()


# ---------- HTTP Handler ----------
class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)

        try:
            if path == "/":
                return self._send_json(200, api_root())
            
            parts = [p for p in path.split("/") if p]
            
            if parts == ["api", "symbols"]:
                return self._send_json(200, api_symbols(query))
            
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "symbols":
                data = api_symbol(parts[2])
                if data is None:
                    return self._send_json(404, {"error": "Symbol not found"})
                return self._send_json(200, data)
            
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "history":
                return self._send_json(200, api_history(parts[2], query))
            
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "indicators":
                return self._send_json(200, api_indicators(parts[2], query))
            
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "latest":
                data = api_latest(parts[2])
                if data is None:
                    return self._send_json(404, {"error": "Symbol not found"})
                return self._send_json(200, data)
            
            return self._send_json(404, {"error": "Not found"})
        
        except Exception as e:
            return self._send_json(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        print(f"[API] {fmt % args}")


# ---------- Run ----------
def main():
    if not DB_PATH.exists():
        print(f"[ERROR] DB not found: {DB_PATH}")
        return
    print("=" * 60)
    print(f"BEHZAD_AI API v{VERSION}")
    print(f"Listening on http://{HOST}:{PORT}")
    print("=" * 60)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[STOP] Server stopped.")


if __name__ == "__main__":
    main()
