# src/data/batch_advanced_indicators.py
# محاسبه تمام ۳۳ اندیکاتور پیشرفته برای همه نمادهایی که تاریخچه دارن

import sqlite3
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH
from src.analysis.advanced_indicators import AdvancedIndicators


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_symbols_with_history(con):
    return [r[0] for r in con.execute(
        "SELECT DISTINCT ins_code FROM price_history"
    ).fetchall()]


def compute_vwap(prices):
    """محاسبه VWAP روزانه"""
    n = len(prices)
    result = [None] * n
    cum_pv = 0
    cum_v = 0
    for i in range(n):
        typical = (prices[i]["price_max"] + prices[i]["price_min"] + prices[i]["price_close"]) / 3
        pv = typical * prices[i]["volume"]
        cum_pv += pv
        cum_v += prices[i]["volume"]
        if cum_v > 0:
            result[i] = cum_pv / cum_v
    return result


def compute_cci(prices, period=20):
    """محاسبه CCI (Commodity Channel Index)"""
    n = len(prices)
    result = [None] * n
    for i in range(period - 1, n):
        window = prices[i - period + 1:i + 1]
        tp_list = [(r["price_max"] + r["price_min"] + r["price_close"]) / 3 for r in window]
        sma_tp = sum(tp_list) / period
        mad = sum(abs(x - sma_tp) for x in tp_list) / period
        if mad > 0:
            result[i] = (tp_list[-1] - sma_tp) / (0.015 * mad)
    return result


def compute_mfi(prices, period=14):
    """محاسبه MFI (Money Flow Index)"""
    n = len(prices)
    if n < period + 1:
        return [None] * n
    result = [None] * n
    typical = [(p["price_max"] + p["price_min"] + p["price_close"]) / 3 for p in prices]
    
    for i in range(period, n):
        pos_mf = 0
        neg_mf = 0
        for j in range(i - period + 1, i + 1):
            mf = typical[j] * prices[j]["volume"]
            if typical[j] > typical[j-1]:
                pos_mf += mf
            elif typical[j] < typical[j-1]:
                neg_mf += mf
        if neg_mf > 0:
            mr = pos_mf / neg_mf
            result[i] = 100 - (100 / (1 + mr))
        else:
            result[i] = 100.0
    return result


def compute_williams_r(prices, period=14):
    """محاسبه Williams %R"""
    n = len(prices)
    result = [None] * n
    for i in range(period - 1, n):
        window = prices[i - period + 1:i + 1]
        high = max(r["price_max"] for r in window)
        low = min(r["price_min"] for r in window)
        if high - low > 0:
            result[i] = -100 * (high - prices[i]["price_close"]) / (high - low)
    return result


def compute_roc(prices, period=12):
    """محاسبه ROC (Rate of Change)"""
    n = len(prices)
    result = [None] * n
    for i in range(period, n):
        old = prices[i - period]["price_close"]
        if old > 0:
            result[i] = (prices[i]["price_close"] - old) / old * 100
    return result


def compute_psar(prices, af_step=0.02, af_max=0.2):
    """محاسبه Parabolic SAR (ساده‌شده)"""
    n = len(prices)
    if n < 2:
        return [None] * n
    result = [None] * n
    # شروع با روند صعودی
    bull = True
    ep = prices[0]["price_max"]
    sar = prices[0]["price_min"]
    af = af_step
    result[0] = sar
    
    for i in range(1, n):
        sar = sar + af * (ep - sar)
        if bull:
            if prices[i]["price_min"] < sar:
                bull = False
                sar = ep
                ep = prices[i]["price_min"]
                af = af_step
            else:
                if prices[i]["price_max"] > ep:
                    ep = prices[i]["price_max"]
                    af = min(af + af_step, af_max)
        else:
            if prices[i]["price_max"] > sar:
                bull = True
                sar = ep
                ep = prices[i]["price_max"]
                af = af_step
            else:
                if prices[i]["price_min"] < ep:
                    ep = prices[i]["price_min"]
                    af = min(af + af_step, af_max)
        result[i] = sar
    return result


def compute_trend(close, ma20, ma50, adx_val):
    """تشخیص روند و قدرت"""
    direction = "SIDEWAYS"
    strength = "WEAK"
    
    if close and ma20 and ma50:
        if close > ma20 > ma50:
            direction = "UP"
        elif close < ma20 < ma50:
            direction = "DOWN"
    
    if adx_val:
        if adx_val > 25:
            strength = "STRONG"
        elif adx_val > 20:
            strength = "MEDIUM"
    
    return direction, strength


def compute_all_for_symbol(ins_code):
    """محاسبه همه اندیکاتورها برای یک نماد"""
    ind = AdvancedIndicators(ins_code)
    count = ind.load_from_db()
    if count < 50:
        return 0
    
    prices = ind.prices
    
    # محاسبه همه اندیکاتورها
    atr = ind.atr(14)
    adx_data = ind.adx(14)
    obv = ind.obv()
    stoch = ind.stochastic()
    ichi = ind.ichimoku()
    fib = ind.fibonacci_levels(100)
    vwap = compute_vwap(prices)
    cci = compute_cci(prices, 20)
    mfi = compute_mfi(prices, 14)
    will_r = compute_williams_r(prices, 14)
    roc = compute_roc(prices, 12)
    psar = compute_psar(prices)
    
    # برای MA ها و بقیه، از Indicators قبلی استفاده می‌کنیم
    from src.analysis.indicators import Indicators
    basic = Indicators(ins_code)
    basic.load_from_db()
    ma5 = basic.sma(5)
    ma10 = basic.sma(10)
    ma20 = basic.sma(20)
    ma50 = basic.sma(50)
    rsi = basic.rsi(14)
    macd_data = basic.macd()
    bb = basic.bollinger()
    
    # ذخیره
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.execute("PRAGMA journal_mode=WAL")
    now = now_iso()
    saved = 0
    
    with con:
        for i in range(count):
            row = {
                "ma5": ma5[i], "ma10": ma10[i], "ma20": ma20[i], "ma50": ma50[i],
                "rsi14": rsi[i],
                "macd": macd_data["macd"][i],
                "macd_signal": macd_data["signal"][i],
                "macd_histogram": macd_data["histogram"][i],
                "bb_upper": bb["upper"][i],
                "bb_middle": bb["middle"][i],
                "bb_lower": bb["lower"][i],
                "atr14": atr[i],
                "adx14": adx_data["adx"][i],
                "plus_di": adx_data["plus_di"][i],
                "minus_di": adx_data["minus_di"][i],
                "obv": obv[i],
                "stoch_k": stoch["k"][i],
                "stoch_d": stoch["d"][i],
                "ichimoku_tenkan": ichi["tenkan"][i],
                "ichimoku_kijun": ichi["kijun"][i],
                "ichimoku_senkou_a": ichi["senkou_a"][i],
                "ichimoku_senkou_b": ichi["senkou_b"][i],
                "fib_236": fib.get("level_236"),
                "fib_382": fib.get("level_382"),
                "fib_500": fib.get("level_500"),
                "fib_618": fib.get("level_618"),
                "fib_786": fib.get("level_786"),
                "vwap": vwap[i],
                "cci20": cci[i],
                "mfi14": mfi[i],
                "williams_r": will_r[i],
                "roc12": roc[i],
                "psar": psar[i],
            }
            
            # روند
            direction, strength = compute_trend(
                prices[i]["price_close"], ma20[i], ma50[i], adx_data["adx"][i]
            )
            row["trend_direction"] = direction
            row["trend_strength"] = strength
            
            # بررسی اینکه آیا حداقل یکی از اندیکاتورها مقدار داره
            if not any(v is not None for k, v in row.items() if k not in ("fib_236", "fib_382", "fib_500", "fib_618", "fib_786")):
                continue
            
            con.execute("""
                INSERT INTO indicators (
                    ins_code, date, ma5, ma10, ma20, ma50, rsi14,
                    macd, macd_signal, macd_histogram,
                    bb_upper, bb_middle, bb_lower,
                    atr14, adx14, plus_di, minus_di, obv,
                    stoch_k, stoch_d,
                    ichimoku_tenkan, ichimoku_kijun, ichimoku_senkou_a, ichimoku_senkou_b,
                    fib_236, fib_382, fib_500, fib_618, fib_786,
                    vwap, cci20, mfi14, williams_r, roc12, psar,
                    trend_direction, trend_strength, computed_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(ins_code, date) DO UPDATE SET
                    atr14=excluded.atr14, adx14=excluded.adx14,
                    plus_di=excluded.plus_di, minus_di=excluded.minus_di,
                    obv=excluded.obv,
                    stoch_k=excluded.stoch_k, stoch_d=excluded.stoch_d,
                    ichimoku_tenkan=excluded.ichimoku_tenkan, ichimoku_kijun=excluded.ichimoku_kijun,
                    ichimoku_senkou_a=excluded.ichimoku_senkou_a, ichimoku_senkou_b=excluded.ichimoku_senkou_b,
                    fib_236=excluded.fib_236, fib_382=excluded.fib_382,
                    fib_500=excluded.fib_500, fib_618=excluded.fib_618,
                    fib_786=excluded.fib_786,
                    vwap=excluded.vwap, cci20=excluded.cci20, mfi14=excluded.mfi14,
                    williams_r=excluded.williams_r, roc12=excluded.roc12, psar=excluded.psar,
                    trend_direction=excluded.trend_direction, trend_strength=excluded.trend_strength,
                    computed_at=excluded.computed_at
            """, (
                ins_code, prices[i]["date"],
                row["ma5"], row["ma10"], row["ma20"], row["ma50"], row["rsi14"],
                row["macd"], row["macd_signal"], row["macd_histogram"],
                row["bb_upper"], row["bb_middle"], row["bb_lower"],
                row["atr14"], row["adx14"], row["plus_di"], row["minus_di"], row["obv"],
                row["stoch_k"], row["stoch_d"],
                row["ichimoku_tenkan"], row["ichimoku_kijun"], row["ichimoku_senkou_a"], row["ichimoku_senkou_b"],
                row["fib_236"], row["fib_382"], row["fib_500"], row["fib_618"], row["fib_786"],
                row["vwap"], row["cci20"], row["mfi14"], row["williams_r"], row["roc12"], row["psar"],
                row["trend_direction"], row["trend_strength"], now,
            ))
            saved += 1
    
    con.close()
    return saved


def main():
    print("=" * 70)
    print("BATCH ADVANCED INDICATORS - محاسبه ۳۳ اندیکاتور")
    print("=" * 70)
    
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    symbols = get_symbols_with_history(con)
    
    # بررسی اینکه قبلاً محاسبه شدن یا نه
    already = set(r[0] for r in con.execute(
        "SELECT DISTINCT ins_code FROM indicators WHERE atr14 IS NOT NULL"
    ).fetchall())
    pending = [s for s in symbols if s not in already]
    
    con.close()
    
    print(f"تعداد نمادهای با تاریخچه: {len(symbols)}")
    print(f"قبلاً محاسبه‌شده (کامل): {len(already)}")
    print(f"در انتظار محاسبه: {len(pending)}")
    print()
    
    if not pending:
        print("🎉 همه نمادها محاسبه شدن!")
        return
    
    success = 0
    failed = 0
    total_rows = 0
    start_time = time.time()
    
    for i, ins_code in enumerate(pending, 1):
        try:
            saved = compute_all_for_symbol(ins_code)
            if saved > 0:
                success += 1
                total_rows += saved
                print(f"[{i}/{len(pending)}] {ins_code} ... ✅ {saved} رکورد")
            else:
                failed += 1
                print(f"[{i}/{len(pending)}] {ins_code} ... ⚠️ داده کافی نیست")
        except Exception as e:
            failed += 1
            print(f"[{i}/{len(pending)}] {ins_code} ... ❌ {type(e).__name__}: {e}")
    
    elapsed = time.time() - start_time
    
    print()
    print("=" * 70)
    print("BATCH COMPLETE")
    print(f"  ✅ موفق: {success}")
    print(f"  ❌ ناموفق: {failed}")
    print(f"  📊 مجموع رکورد: {total_rows:,}")
    print(f"  ⏱️ مدت: {elapsed:.0f} ثانیه")
    print("=" * 70)


if __name__ == "__main__":
    main()
