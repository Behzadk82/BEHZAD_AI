# src/analysis/indicators_multi_tf.py
import sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

def init_tables(con):
    con.executescript("""
        CREATE TABLE IF NOT EXISTS indicators_intraday (
            ins_code TEXT, interval TEXT, date TEXT, rsi14 REAL, macd REAL, macd_signal REAL,
            ma20 REAL, ma50 REAL, supertrend REAL, supertrend_direction TEXT,
            PRIMARY KEY (ins_code, interval, date)
        );
        CREATE TABLE IF NOT EXISTS indicators_weekly (
            ins_code TEXT, date INTEGER, rsi14 REAL, macd REAL, macd_signal REAL,
            ma20 REAL, ma50 REAL, supertrend REAL, supertrend_direction TEXT, PRIMARY KEY (ins_code, date)
        );
        CREATE TABLE IF NOT EXISTS indicators_monthly (
            ins_code TEXT, date INTEGER, rsi14 REAL, macd REAL, macd_signal REAL,
            ma20 REAL, ma50 REAL, supertrend REAL, supertrend_direction TEXT, PRIMARY KEY (ins_code, date)
        );
    """)
    con.commit()

def calc_sma(prices, period):
    res = [None]*len(prices)
    for i in range(period-1, len(prices)): res[i] = sum(prices[i-period+1:i+1])/period
    return res

def calc_rsi(prices, period=14):
    res = [None]*len(prices)
    if len(prices) < period+1: return res
    g, l = [], []
    for i in range(1, len(prices)):
        c = prices[i]-prices[i-1]; g.append(max(c,0)); l.append(max(-c,0))
    ag, al = sum(g[:period])/period, sum(l[:period])/period
    res[period] = 100-(100/(1+ag/al)) if al > 0 else 100
    for i in range(period, len(g)):
        ag = (ag*(period-1)+g[i])/period; al = (al*(period-1)+l[i])/period
        res[i+1] = 100-(100/(1+ag/al)) if al > 0 else 100
    return res

def calc_ema(prices, period):
    res = [None]*len(prices)
    if len(prices) < period: return res
    k = 2/(period+1); res[period-1] = sum(prices[:period])/period
    for i in range(period, len(prices)): res[i] = (prices[i]-res[i-1])*k+res[i-1]
    return res

def calc_macd(prices):
    e12, e26 = calc_ema(prices,12), calc_ema(prices,26)
    macd = [None]*len(prices)
    for i in range(len(prices)):
        if e12[i] is not None and e26[i] is not None: macd[i] = e12[i]-e26[i]
    sig = [None]*len(prices)
    v = [(i,x) for i,x in enumerate(macd) if x is not None]
    if len(v) >= 9:
        k = 2/10; s = sum(x for _,x in v[:9])/9; sig[v[8][0]] = s
        for i in range(9, len(v)):
            idx = v[i][0]; sig[idx] = (v[i][1]-sig[v[i-1][0]])*k+sig[v[i-1][0]]
    return macd, sig

def calc_atr(prices, period=14):
    n = len(prices); tr = [0]*n
    for i in range(1, n):
        tr[i] = max(prices[i]["high"]-prices[i]["low"], abs(prices[i]["high"]-prices[i-1]["close"]), abs(prices[i]["low"]-prices[i-1]["close"]))
    atr = [None]*n
    if n > period: atr[period] = sum(tr[1:period+1])/period
    for i in range(period+1, n): atr[i] = (atr[i-1]*(period-1)+tr[i])/period
    return atr

def calc_st(prices, atr, mult=3):
    n = len(prices); st, d = [None]*n, [None]*n
    for i in range(n):
        if atr[i] is None: continue
        hl2 = (prices[i]["high"]+prices[i]["low"])/2
        u = hl2+mult*atr[i]; lo = hl2-mult*atr[i]
        if i == 0 or st[i-1] is None: st[i] = lo; d[i] = "UP"; continue
        if d[i-1] == "UP":
            if prices[i]["close"] < st[i-1]: st[i] = u; d[i] = "DOWN"
            else: st[i] = max(lo, st[i-1]); d[i] = "UP"
        else:
            if prices[i]["close"] > st[i-1]: st[i] = lo; d[i] = "UP"
            else: st[i] = min(u, st[i-1]); d[i] = "DOWN"
    return st, d

def process_table(con, src, dst, dcol):
    syms = [r[0] for r in con.execute(f"SELECT DISTINCT ins_code FROM {src}").fetchall()]
    print(f"Processing {src}: {len(syms)} symbols")
    for idx, code in enumerate(syms, 1):
        rows = con.execute(f"SELECT * FROM {src} WHERE ins_code=? ORDER BY {dcol} ASC", (code,)).fetchall()
        if len(rows) < 50: continue
        prices = [{"close": r["price_close"], "high": r["price_high"], "low": r["price_low"], "date": r[dcol]} for r in rows]
        closes = [p["close"] for p in prices]
        rsi = calc_rsi(closes); ma20 = calc_sma(closes,20); ma50 = calc_sma(closes,50)
        macd, sig = calc_macd(closes); atr = calc_atr(prices); st, d = calc_st(prices, atr)
        for i, p in enumerate(prices):
            con.execute(f"INSERT OR REPLACE INTO {dst} (ins_code, date, rsi14, macd, macd_signal, ma20, ma50, supertrend, supertrend_direction) VALUES (?,?,?,?,?,?,?,?,?)",
                        (code, p["date"], rsi[i], macd[i], sig[i], ma20[i], ma50[i], st[i], d[i]))
        if idx % 100 == 0: print(f"  [{idx}/{len(syms)}] OK")

def main():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    init_tables(con)
    process_table(con, "price_history_weekly", "indicators_weekly", "week_start")
    process_table(con, "price_history_monthly", "indicators_monthly", "month_start")
    con.commit(); con.close()
    print("DONE")

if __name__ == "__main__":
    main()
