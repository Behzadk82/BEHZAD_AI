# src/analysis/signal_engine.py
import sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

def get_final_signal(ins_code):
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    
    row = con.execute("""
        SELECT i.supertrend_direction, i.rsi14, i.macd, i.macd_signal,
               i.adx14, i.plus_di, i.minus_di, i.rvol, i.stoch_rsi, i.aroon_up, i.aroon_down
        FROM indicators i WHERE i.ins_code = ? ORDER BY date DESC LIMIT 1
    """, (ins_code,)).fetchone()
    
    sym = con.execute("SELECT symbol FROM symbols WHERE ins_code = ?", (ins_code,)).fetchone()
    con.close()
    
    if not row or not sym: return None
    
    buy_signals = 0; sell_signals = 0; reasons = []
    
    if row["supertrend_direction"] == "UP": buy_signals += 1
    else: sell_signals += 1
    
    if row["rsi14"] and row["rsi14"] < 40: buy_signals += 1
    elif row["rsi14"] and row["rsi14"] > 70: sell_signals += 1
    
    if row["macd"] and row["macd_signal"] and row["macd"] > row["macd_signal"]: buy_signals += 1
    else: sell_signals += 1
    
    if row["aroon_up"] and row["aroon_down"] and row["aroon_up"] > row["aroon_down"]: buy_signals += 1
    else: sell_signals += 1
    
    if row["stoch_rsi"] and row["stoch_rsi"] < 20: buy_signals += 1
    elif row["stoch_rsi"] and row["stoch_rsi"] > 80: sell_signals += 1
    
    if buy_signals > sell_signals: signal = "BUY"
    elif sell_signals > buy_signals: signal = "SELL"
    else: signal = "HOLD"
    
    return {
        "symbol": sym["symbol"], "signal": signal,
        "buy_signals": buy_signals, "sell_signals": sell_signals,
        "confidence": abs(buy_signals - sell_signals) / max(buy_signals + sell_signals, 1) * 100,
    }

if __name__ == "__main__":
    print("SIGNAL ENGINE TEST")
    for code in ["46348559193224090", "35425587644337450", "7745894403636165"]:
        r = get_final_signal(code)
        if r: print(f"{r['symbol']}: {r['signal']} (Buy={r['buy_signals']}, Sell={r['sell_signals']}, Confidence={r['confidence']:.0f}%)")
