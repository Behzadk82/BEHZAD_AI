# src/analysis/indicators_multi_tf.py
import sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

def init_tables(con):
    con.executescript("""
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
    for i in range(period-1, len(prices)):
        res[i] = sum(prices[i-period+1:i+1])/period
    return res

def calc_rsi(prices, period=14):
    res = [None]*len(prices)
    if len(prices) < period+1: return res
    gains = []; losses = []
    for i in range(1, len(prices)):
        c = prices[i] - prices[i-1]
        gains.append(max(c, 0)); losses.append(max(-c, 0))
    avg_g = sum(gains[:period])/period; avg_l = sum(losses[:period])/period
    res[period] = 100 - (100/(1+avg_g/avg_l)) if avg_l > 0 else 100
    for i in range(period, len(gains)):
        avg_g = (avg_g*(period-1)+gains[i])/period
        avg_l = (avg_l*(period-1)+losses[i])/period
        res[i+1] = 100 - (100/(1+avg_g/avg_l)) if avg_l > 0 else 100
    return res

def calc_ema(prices, period):
    res = [None]*len(prices)
    if len(prices) < period: return res
    k = 2/(period+1)
    res[period-1] = sum(prices[:period])/period
    for i in range(period, len(prices)):
        res[i] = (prices[i]-res[i-1])*k + res[i-1]
    return res

def calc_macd(prices):
    ema12 = calc_ema(prices, 12); ema26 = calc_ema(prices, 26)
    macd = [None]*len(prices)
    for i in range(len(prices)):
        if ema12[i] is not None and ema26[i] is not None: macd[i] = ema12[i] - ema26[i]
    signal = [None]*len(prices)
    valid = [(i,v) for i,v in enumerate(macd) if v is not None]
    if len(valid) >= 9:
        k = 2/10
        start = valid[8][0]; s = sum(v for _,v in valid[:9])/9
        signal[start] = s
        for i in range(9, len(valid)):
            idx = valid[i][0]; signal[idx] = (valid[i][1]-signal[valid[i-1][0]])*k + signal[valid[i-1][0]]
    return macd, signal

def calc_supertrend(prices, atr, mult=3):
    n = len(prices); st = [None]*n; d = [None]*n
    for i in range(n):
        if atr[i] is None: continue
        hl2 = (prices[i]["high"]+prices[i]["low"])/2
        u = hl2 + mult*atr[i]; l = hl2 - mult*atr[i]
        if i == 0 or st[i-1] is None: st[i] = l; d[i] = "UP"; continue
        if d[i-1] == "UP":
            if prices[i]["close"] < st[i-1]: st[i] = u; d[i] = "DOWN"
            else: st[i] = max(l, st[i-1]); d[i] = "UP"
        else:
            if prices[i]["close"] > st[i-1]: st[i] = l; d[i] = "UP"
            else: st[i] = min(u, st[i-1]); d[i] = "DOWN"
    return st, d

def calc_atr(prices, period=14):
    n = len(prices); tr = [None]+[None]*n
    tr = [0]*n
    for i in range(1, n):
        tr[i] = max(prices[i]["high"]-prices[i]["low"], abs(prices[i]["high"]-prices[i-1]["close"]), abs(prices[i]["low"]-prices[i-1]["close"]))
    atr = [None]*n
    if n > period: atr[period] = sum(tr[1:period+1])/period
    for i in range(period+1, n):
        atr[i] = (atr[i-1]*(period-1)+tr[i])/period
    return atr

def main():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    init_tables(con)
    
    for table, target in [("price_history_weekly", "indicators_weekly"), ("price_history_monthly", "indicators_monthly")]:
        symbols = [r[0] for r in con.execute(f"SELECT DISTINCT ins_code FROM {table}").fetchall()]
        print(f"Processing {table}: {len(symbols)} symbols")
        
        for idx, code in enumerate(symbols, 1):
            rows = con.execute(f"SELECT * FROM {table} WHERE ins_code=? ORDER BY week_start ASC" if "week" in table else f"SELECT * FROM {table} WHERE ins_code=? ORDER BY month_start ASC", (code,)).fetchall()
            if len(rows) < 50: continue
            
            prices = [{"close": r["price_close"], "high": r["price_high"], "low": r["price_low"], "date": r[1]} for r in rows]
            closes = [p["close"] for p in prices]
            
            rsi = calc_rsi(closes); ma20 = calc_sma(closes, 20); ma50 = calc_sma(closes, 50)
            macd, signal = calc_macd(closes)
            atr = calc_atr(prices); st, d = calc_supertrend(prices, atr)
            
            for i, p in enumerate(prices):
                con.execute(f"""INSERT OR REPLACE INTO {target} (ins_code, date, rsi14, macd, macd_signal, ma20, ma50, supertrend, supertrend_direction)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (code, p["date"], rsi[i], macd[i], signal[i], ma20[i], ma50[i], st[i], d[i]))
            
            if idx % 100 == 0: print(f"  [{idx}/{len(symbols)}] OK")
    
    con.commit(); con.close()
    print("DONE")

if __name__ == "__main__":
    main()
