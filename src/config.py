# src/config.py
# Central configuration for BEHZAD_AI

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
LOGS_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "behzad_ai.db"

for d in (DATA_DIR, CACHE_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)

TSETMC_BASE = "https://cdn.tsetmc.com/api"
USER_AGENT = "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Referer": "https://cdn.tsetmc.com/",
}

TIMEOUT_MARKET_WATCH = 40
TIMEOUT_DAILY_LIST = 40
TIMEOUT_CLOSING_PRICE = 15
TIMEOUT_INSTRUMENT_INFO = 15
TIMEOUT_DEFAULT = 30

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2
RETRY_STATUS_CODES = [500, 502, 503, 504]
STOP_STATUS_CODES = [401, 403, 429]

DELAY_BETWEEN_SYMBOLS = 1.0
DELAY_BETWEEN_MARKETS = 3.0
DELAY_BEFORE_RETRY = 2.0

BATCH_SIZE = 20
BATCH_CHECKPOINT_FILE = DATA_DIR / "batch_checkpoint.json"

CACHE_TTL_SECONDS = 300
CACHE_ENABLED = True

DB_TIMEOUT = 15
DB_WAL_MODE = True
DB_FOREIGN_KEYS = True

LOG_LEVEL = "INFO"
LOG_FILE = LOGS_DIR / "behzad_ai.log"


def describe():
    print("=" * 60)
    print("BEHZAD_AI CONFIGURATION")
    print("=" * 60)
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"DB_PATH: {DB_PATH}")
    print(f"DB exists: {DB_PATH.exists()}")
    print()
    print(f"MAX_RETRIES: {MAX_RETRIES}")
    print(f"BATCH_SIZE: {BATCH_SIZE}")
    print(f"TIMEOUT_DAILY_LIST: {TIMEOUT_DAILY_LIST}s")
    print("=" * 60)


if __name__ == "__main__":
    describe()
