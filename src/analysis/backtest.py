# src/analysis/backtest.py
# Backtest engine - Phase 4.1
# Simulates a strategy on historical data.

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH


class Backtest:
    def __init__(self, ins_code, initial_capital=100_000_000):
        self.ins_code = ins_code
        self.initial_capital = initial_capital
        self.con = sqlite3.connect(DB_PATH, timeout=15)
        self.con.row_factory = sqlite3.Row

    def close(self):
        if self.con:
            self.con.close()

    def _load_data(self):
        """Load joined price + indicators, ordered by date."""
        rows = self.con.execute("""
            SELECT 
                p.date, p.price_close, p.volume,
                i.rsi14, i.macd, i.macd_signal, i.ma5, i.ma20
            FROM price_history p
            JOIN indicators i ON p.ins_code = i.ins_code AND p.date = i.date
            WHERE p.ins_code = ?
            ORDER BY p.date ASC
        """, (self.ins_code,)).fetchall()
        return [dict(r) for r in rows]

    # ---------- Strategy 1: RSI ----------
    def run_rsi(self, buy_threshold=30, sell_threshold=70):
        """Buy when RSI < buy_threshold, sell when RSI > sell_threshold."""
        data = self._load_data()
        if not data:
            return None

        cash = self.initial_capital
        shares = 0
        trades = []
        equity_curve = []

        for row in data:
            price = row["price_close"]
            rsi = row["rsi14"]

            # Buy signal
            if rsi is not None and rsi < buy_threshold and shares == 0:
                shares = int(cash // price)
                if shares > 0:
                    cash -= shares * price
                    trades.append({"date": row["date"], "action": "BUY", "price": price, "shares": shares, "rsi": round(rsi, 1)})

            # Sell signal
            elif rsi is not None and rsi > sell_threshold and shares > 0:
                cash += shares * price
                trades.append({"date": row["date"], "action": "SELL", "price": price, "shares": shares, "rsi": round(rsi, 1)})
                shares = 0

            # Track equity
            equity = cash + shares * price
            equity_curve.append({"date": row["date"], "equity": equity})

        # Close any open position at the end
        if shares > 0:
            last_price = data[-1]["price_close"]
            cash += shares * last_price
            trades.append({"date": data[-1]["date"], "action": "SELL (END)", "price": last_price, "shares": shares, "rsi": None})
            shares = 0

        return self._calculate_metrics(equity_curve, trades, cash)

    # ---------- Strategy 2: MA Cross ----------
    def run_ma_cross(self):
        """Buy when MA5 crosses above MA20, sell when below."""
        data = self._load_data()
        if not data:
            return None

        cash = self.initial_capital
        shares = 0
        trades = []
        equity_curve = []

        prev_ma5, prev_ma20 = None, None

        for row in data:
            price = row["price_close"]
            ma5 = row["ma5"]
            ma20 = row["ma20"]

            if ma5 is not None and ma20 is not None and prev_ma5 is not None and prev_ma20 is not None:
                # Golden cross: MA5 crosses above MA20
                if prev_ma5 <= prev_ma20 and ma5 > ma20 and shares == 0:
                    shares = int(cash // price)
                    if shares > 0:
                        cash -= shares * price
                        trades.append({"date": row["date"], "action": "BUY", "price": price, "shares": shares, "reason": "MA golden cross"})
                # Death cross: MA5 crosses below MA20
                elif prev_ma5 >= prev_ma20 and ma5 < ma20 and shares > 0:
                    cash += shares * price
                    trades.append({"date": row["date"], "action": "SELL", "price": price, "shares": shares, "reason": "MA death cross"})
                    shares = 0

            prev_ma5, prev_ma20 = ma5, ma20

            equity = cash + shares * price
            equity_curve.append({"date": row["date"], "equity": equity})

        if shares > 0:
            last_price = data[-1]["price_close"]
            cash += shares * last_price
            trades.append({"date": data[-1]["date"], "action": "SELL (END)", "price": last_price, "shares": shares, "reason": "end"})
            shares = 0

        return self._calculate_metrics(equity_curve, trades, cash)

    # ---------- Strategy 3: MACD ----------
    def run_macd(self):
        """Buy on MACD > Signal, sell on MACD < Signal."""
        data = self._load_data()
        if not data:
            return None

        cash = self.initial_capital
        shares = 0
        trades = []
        equity_curve = []

        prev_macd, prev_signal = None, None

        for row in data:
            price = row["price_close"]
            macd = row["macd"]
            signal = row["macd_signal"]

            if macd is not None and signal is not None and prev_macd is not None and prev_signal is not None:
                if prev_macd <= prev_signal and macd > signal and shares == 0:
                    shares = int(cash // price)
                    if shares > 0:
                        cash -= shares * price
                        trades.append({"date": row["date"], "action": "BUY", "price": price, "shares": shares, "reason": "MACD cross"})
                elif prev_macd >= prev_signal and macd < signal and shares > 0:
                    cash += shares * price
                    trades.append({"date": row["date"], "action": "SELL", "price": price, "shares": shares, "reason": "MACD cross"})
                    shares = 0

            prev_macd, prev_signal = macd, signal
            equity = cash + shares * price
            equity_curve.append({"date": row["date"], "equity": equity})

        if shares > 0:
            last_price = data[-1]["price_close"]
            cash += shares * last_price
            trades.append({"date": data[-1]["date"], "action": "SELL (END)", "price": last_price, "shares": shares, "reason": "end"})
            shares = 0

        return self._calculate_metrics(equity_curve, trades, cash)

    # ---------- Metrics ----------
    def _calculate_metrics(self, equity_curve, trades, final_cash):
        if not equity_curve:
            return None

        final_equity = equity_curve[-1]["equity"]
        total_return_pct = (final_equity - self.initial_capital) / self.initial_capital * 100

        # Max drawdown
        peak = 0
        max_dd = 0
        for pt in equity_curve:
            if pt["equity"] > peak:
                peak = pt["equity"]
            dd = (peak - pt["equity"]) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        # Win rate
        buy_price = None
        wins, losses = 0, 0
        for t in trades:
            if t["action"] == "BUY":
                buy_price = t["price"]
            elif t["action"].startswith("SELL") and buy_price:
                if t["price"] > buy_price:
                    wins += 1
                else:
                    losses += 1
                buy_price = None

        total_closed = wins + losses
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0

        return {
            "initial_capital": self.initial_capital,
            "final_equity": final_equity,
            "final_cash": final_cash,
            "total_return_pct": round(total_return_pct, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "total_trades": len([t for t in trades if t["action"] == "BUY"]),
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 1),
            "trades": trades,
            "equity_curve": equity_curve,
        }


if __name__ == "__main__":
    ins_code = "46348559193224090"
    symbol = "فولاد"

    print("=" * 70)
    print(f"BACKTEST - {symbol} ({ins_code})")
    print("=" * 70)

    bt = Backtest(ins_code, initial_capital=100_000_000)

    # Test RSI
    print("\n--- STRATEGY 1: RSI (buy<30, sell>70) ---")
    r1 = bt.run_rsi()
    if r1:
        print(f"  Initial:  {r1['initial_capital']:>15,.0f} ریال")
        print(f"  Final:    {r1['final_equity']:>15,.0f} ریال")
        print(f"  Return:   {r1['total_return_pct']:>14.2f}%")
        print(f"  Max DD:   {r1['max_drawdown_pct']:>14.2f}%")
        print(f"  Trades:   {r1['total_trades']:>14}")
        print(f"  Win rate: {r1['win_rate']:>14.1f}% ({r1['wins']}W/{r1['losses']}L)")

    # Test MA Cross
    print("\n--- STRATEGY 2: MA Cross (MA5 vs MA20) ---")
    r2 = bt.run_ma_cross()
    if r2:
        print(f"  Initial:  {r2['initial_capital']:>15,.0f} ریال")
        print(f"  Final:    {r2['final_equity']:>15,.0f} ریال")
        print(f"  Return:   {r2['total_return_pct']:>14.2f}%")
        print(f"  Max DD:   {r2['max_drawdown_pct']:>14.2f}%")
        print(f"  Trades:   {r2['total_trades']:>14}")
        print(f"  Win rate: {r2['win_rate']:>14.1f}% ({r2['wins']}W/{r2['losses']}L)")

    # Test MACD
    print("\n--- STRATEGY 3: MACD Cross ---")
    r3 = bt.run_macd()
    if r3:
        print(f"  Initial:  {r3['initial_capital']:>15,.0f} ریال")
        print(f"  Final:    {r3['final_equity']:>15,.0f} ریال")
        print(f"  Return:   {r3['total_return_pct']:>14.2f}%")
        print(f"  Max DD:   {r3['max_drawdown_pct']:>14.2f}%")
        print(f"  Trades:   {r3['total_trades']:>14}")
        print(f"  Win rate: {r3['win_rate']:>14.1f}% ({r3['wins']}W/{r3['losses']}L)")

    bt.close()
    print("\n" + "=" * 70)
    print("BACKTEST COMPLETE")
    print("=" * 70)
