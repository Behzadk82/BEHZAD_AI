#!/usr/bin/env python3
"""Create/upgrade BEHZAD_AI SQLite database. Safe: does not delete existing data."""
from pathlib import Path
import sqlite3

BASE = Path('/storage/emulated/0/BEHZAD_AI')
DB_PATH = BASE / 'data' / 'behzad_ai.sqlite3'

SCHEMA = r'''PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS industries (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS symbols (
 id INTEGER PRIMARY KEY, ticker TEXT NOT NULL UNIQUE, company_name TEXT, isin TEXT,
 market TEXT, board TEXT, industry_id INTEGER, sector TEXT, status TEXT,
 shares_count INTEGER, capital_rial INTEGER, market_cap_rial INTEGER,
 first_seen TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(industry_id) REFERENCES industries(id)
);
CREATE TABLE IF NOT EXISTS daily_prices (
 id INTEGER PRIMARY KEY, symbol_id INTEGER NOT NULL, trade_date TEXT NOT NULL,
 open_price REAL, high_price REAL, low_price REAL, close_price REAL,
 last_price REAL, previous_close REAL, price_change REAL, change_pct REAL,
 volume INTEGER, value_rial REAL, trade_count INTEGER,
 UNIQUE(symbol_id, trade_date), FOREIGN KEY(symbol_id) REFERENCES symbols(id)
);
CREATE TABLE IF NOT EXISTS market_snapshots (
 id INTEGER PRIMARY KEY, captured_at TEXT NOT NULL, index_name TEXT NOT NULL,
 index_value REAL, change_value REAL, change_pct REAL, market_volume INTEGER,
 market_value_rial REAL, trade_count INTEGER, source TEXT
);
CREATE TABLE IF NOT EXISTS symbol_snapshots (
 id INTEGER PRIMARY KEY, symbol_id INTEGER NOT NULL, captured_at TEXT NOT NULL,
 last_price REAL, close_price REAL, open_price REAL, high_price REAL, low_price REAL,
 volume INTEGER, value_rial REAL, trade_count INTEGER, status TEXT,
 buy_individual_count INTEGER, buy_individual_volume INTEGER,
 sell_individual_count INTEGER, sell_individual_volume INTEGER,
 buy_institution_count INTEGER, buy_institution_volume INTEGER,
 sell_institution_count INTEGER, sell_institution_volume INTEGER,
 FOREIGN KEY(symbol_id) REFERENCES symbols(id)
);
CREATE TABLE IF NOT EXISTS financial_reports (
 id INTEGER PRIMARY KEY, symbol_id INTEGER NOT NULL, report_type TEXT, period TEXT,
 fiscal_year INTEGER, publish_date TEXT, source_url TEXT, payload_json TEXT,
 UNIQUE(symbol_id, report_type, period, publish_date),
 FOREIGN KEY(symbol_id) REFERENCES symbols(id)
);
CREATE TABLE IF NOT EXISTS fundamental_metrics (
 id INTEGER PRIMARY KEY, symbol_id INTEGER NOT NULL, as_of_date TEXT NOT NULL,
 metric_name TEXT NOT NULL, metric_value REAL, unit TEXT, source TEXT,
 UNIQUE(symbol_id, as_of_date, metric_name), FOREIGN KEY(symbol_id) REFERENCES symbols(id)
);
CREATE TABLE IF NOT EXISTS major_shareholders (
 id INTEGER PRIMARY KEY, symbol_id INTEGER NOT NULL, as_of_date TEXT,
 shareholder_name TEXT, shares INTEGER, ownership_pct REAL, source TEXT,
 FOREIGN KEY(symbol_id) REFERENCES symbols(id)
);
CREATE TABLE IF NOT EXISTS technical_indicators (
 id INTEGER PRIMARY KEY, symbol_id INTEGER NOT NULL, trade_date TEXT NOT NULL,
 indicator TEXT NOT NULL, timeframe TEXT DEFAULT '1d', value REAL, extra_json TEXT,
 UNIQUE(symbol_id, trade_date, indicator, timeframe), FOREIGN KEY(symbol_id) REFERENCES symbols(id)
);
CREATE TABLE IF NOT EXISTS watchlist (
 id INTEGER PRIMARY KEY, symbol_id INTEGER NOT NULL UNIQUE, note TEXT, added_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(symbol_id) REFERENCES symbols(id)
);
CREATE TABLE IF NOT EXISTS portfolio_accounts (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS portfolio_transactions (
 id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, symbol_id INTEGER NOT NULL,
 transaction_date TEXT NOT NULL, transaction_type TEXT NOT NULL CHECK(transaction_type IN ('BUY','SELL')),
 quantity INTEGER NOT NULL, price REAL NOT NULL, commission REAL DEFAULT 0, note TEXT,
 FOREIGN KEY(account_id) REFERENCES portfolio_accounts(id), FOREIGN KEY(symbol_id) REFERENCES symbols(id)
);
CREATE TABLE IF NOT EXISTS screen_runs (
 id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP, screen_name TEXT,
 criteria_json TEXT, result_count INTEGER, results_json TEXT
);
CREATE TABLE IF NOT EXISTS data_sources (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, url TEXT, access_method TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS data_ingestion_log (
 id INTEGER PRIMARY KEY, source_id INTEGER, started_at TEXT, finished_at TEXT,
 status TEXT, rows_received INTEGER, rows_saved INTEGER, error_text TEXT,
 FOREIGN KEY(source_id) REFERENCES data_sources(id)
);
CREATE TABLE IF NOT EXISTS project_tasks (
 id INTEGER PRIMARY KEY, task_key TEXT UNIQUE, title TEXT NOT NULL, category TEXT,
 status TEXT NOT NULL DEFAULT 'TODO' CHECK(status IN ('TODO','IN_PROGRESS','DONE','BLOCKED')),
 evidence TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol_date ON daily_prices(symbol_id, trade_date);
CREATE INDEX IF NOT EXISTS idx_symbol_snapshots_symbol_time ON symbol_snapshots(symbol_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_reports_symbol_period ON financial_reports(symbol_id, period);
CREATE INDEX IF NOT EXISTS idx_indicators_symbol_date ON technical_indicators(symbol_id, trade_date);
'''

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA user_version=1;')
    print(f'Database ready: {DB_PATH}')
    print('Tables created/checked. Existing records were not deleted.')

if __name__ == '__main__':
    main()
