# src/analysis/backtest_v2.py
import sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

class AdvancedBacktest:
    def __init__(self, ins_code, capital=100_000_000, stop_loss=0.05, take_profit=0.15):
        self.ins_code = ins_code
        self.capital = capital
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.con = sqlite3.connect(DB_PATH, timeout=15)
        self.con.row_factory = sqlite3.Row

    def close(self): self.con.close()

    def run_supertrend(self):
        rows = self.con.execute("""
            SELECT p.date, p.price_close, i.supertrend, i.supertrend_direction
            FROM price_history p JOIN indicators i ON p.ins_code=i.ins_code AND p.date=i.date
            WHERE p.ins_code = ? AND i.supertrend IS NOT NULL ORDER BY p.date ASC
        """, (self.ins_code,)).fetchall()
        
        if not rows: return None
        
        cash = self.capital; shares = 0; entry_price = 0
        trades = []; equity = []
        
        for row in rows:
            price = row["price_close"]
            direction = row["supertrend_direction"]
            
            if shares == 0 and direction == "UP":
                shares = int(cash // price)
                if shares > 0:
                    cash -= shares * price
                    entry_price = price
                    trades.append({"date": row["date"], "action": "BUY", "price": price, "shares": shares})
            elif shares > 0:
                change = (price - entry_price) / entry_price
                if direction == "DOWN" or change <= -self.stop_loss or change >= self.take_profit:
                    cash += shares * price
                    trades.append({"date": row["date"], "action": "SELL", "price": price, "shares": shares, "pnl_pct": round(change*100, 2)})
                    shares = 0
            
            equity.append({"date": row["date"], "equity": cash + shares * price})
        
        if shares > 0:
            last_price = rows[-1]["price_close"]
            cash += shares * last_price
            trades.append({"date": rows[-1]["date"], "action": "SELL (END)", "price": last_price, "shares": shares})
        
        return self._metrics(equity, trades, cash)

    def _metrics(self, equity, trades, final_cash):
        if not equity: return None
        final_eq = equity[-1]["equity"]
        total_ret = (final_eq - self.capital) / self.capital * 100
        
        peak = 0; max_dd = 0
        for pt in equity:
            if pt["equity"] > peak: peak = pt["equity"]
            dd = (peak - pt["equity"]) / peak * 100 if peak > 0 else 0
            if dd > max_dd: max_dd = dd
        
        wins = sum(1 for t in trades if t.get("pnl_pct", 0) > 0)
        losses = sum(1 for t in trades if t.get("pnl_pct", 0) < 0)
        total_closed = wins + losses
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
        
        return {
            "final_equity": final_eq, "total_return_pct": round(total_ret, 2),
            "max_drawdown_pct": round(max_dd, 2), "total_trades": len([t for t in trades if t["action"] == "BUY"]),
            "wins": wins, "losses": losses, "win_rate": round(win_rate, 1), "trades": trades,
        }

if __name__ == "__main__":
    print("=" * 60)
    print("ADVANCED BACKTEST - Supertrend + StopLoss/TakeProfit")
    print("=" * 60)
    
    bt = AdvancedBacktest("46348559193224090")
    r = bt.run_supertrend()
    bt.close()
    
    if r:
        print(f"Initial: {100_000_000:,}")
        print(f"Final: {r['final_equity']:,.0f}")
        print(f"Return: {r['total_return_pct']}%")
        print(f"Max DD: {r['max_drawdown_pct']}%")
        print(f"Trades: {r['total_trades']} ({r['wins']}W/{r['losses']}L)")
        print(f"Win Rate: {r['win_rate']}%")
