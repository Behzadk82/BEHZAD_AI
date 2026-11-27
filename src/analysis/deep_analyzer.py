# src/analysis/deep_analyzer.py
# موتور تحلیل عمیق با استفاده از همه ۳۳ اندیکاتور (نسخه نهایی)

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH


class DeepAnalyzer:
    def __init__(self):
        self.con = sqlite3.connect(DB_PATH, timeout=15)
        self.con.row_factory = sqlite3.Row

    def close(self):
        if self.con:
            self.con.close()

    def _get_all_codes(self):
        return [r["ins_code"] for r in self.con.execute(
            "SELECT DISTINCT ins_code FROM indicators WHERE atr14 IS NOT NULL"
        ).fetchall()]

    def _get_latest_full(self, ins_code):
        """دریافت آخرین رکورد با تمام ۳۳ اندیکاتور"""
        row = self.con.execute("""
            SELECT p.date, p.price_close, p.price_max, p.price_min, p.volume,
                   i.ma5, i.ma10, i.ma20, i.ma50,
                   i.rsi14, i.macd, i.macd_signal, i.macd_histogram,
                   i.bb_upper, i.bb_middle, i.bb_lower,
                   i.atr14, i.adx14, i.plus_di, i.minus_di,
                   i.obv, i.stoch_k, i.stoch_d,
                   i.ichimoku_tenkan, i.ichimoku_kijun, i.ichimoku_senkou_a, i.ichimoku_senkou_b,
                   i.fib_236, i.fib_382, i.fib_500, i.fib_618, i.fib_786,
                   i.vwap, i.cci20, i.mfi14, i.williams_r, i.roc12, i.psar,
                   i.trend_direction, i.trend_strength
            FROM price_history p
            JOIN indicators i ON p.ins_code = i.ins_code AND p.date = i.date
            WHERE p.ins_code = ?
            ORDER BY p.date DESC LIMIT 2
        """, (ins_code,)).fetchall()
        
        sym = self.con.execute(
            "SELECT symbol, name FROM symbols WHERE ins_code = ?", (ins_code,)
        ).fetchone()
        
        if not row or not sym:
            return None
        
        return {
            "symbol": sym["symbol"],
            "name": sym["name"],
            "latest": dict(row[0]),
            "previous": dict(row[1]) if len(row) > 1 else None,
        }

    def _get_history_stats(self, ins_code, days=100):
        """آمار تاریخی برای تحلیل"""
        rows = self.con.execute("""
            SELECT date, price_close, volume FROM price_history
            WHERE ins_code = ? ORDER BY date DESC LIMIT ?
        """, (ins_code, days)).fetchall()
        if not rows:
            return None
        
        prices = [r["price_close"] for r in rows]
        volumes = [r["volume"] for r in rows]
        
        return {
            "high_52w": max(prices),
            "low_52w": min(prices),
            "avg_volume": sum(volumes) / len(volumes),
            "price_20d_ago": prices[19] if len(prices) > 19 else prices[-1],
            "count": len(prices),
        }

    def analyze(self, ins_code):
        """تحلیل کامل یک نماد با ۵ لایه"""
        data = self._get_latest_full(ins_code)
        if not data:
            return None
        
        hist = self._get_history_stats(ins_code, 100)
        if not hist:
            return None
        
        latest = data["latest"]
        previous = data["previous"]
        
        score = 0
        reasons = []
        warnings = []
        
        # ═══════════════════════════════════════════════════════
        # لایه ۱: تکنیکال پایه (RSI + MACD + Stochastic)
        # ═══════════════════════════════════════════════════════
        rsi = latest["rsi14"]
        if rsi is not None:
            if rsi < 30:
                score += 25
                reasons.append(f"RSI({rsi:.0f}) اشباع فروش")
            elif rsi < 40:
                score += 15
                reasons.append(f"RSI({rsi:.0f}) نزدیک اشباع")
            elif rsi > 70:
                score -= 20
                warnings.append(f"RSI({rsi:.0f}) اشباع خرید")
        
        # MACD
        if latest["macd"] is not None and latest["macd_signal"] is not None:
            if latest["macd"] > latest["macd_signal"]:
                score += 15
                reasons.append("MACD صعودی")
            else:
                score -= 10
                warnings.append("MACD نزولی")
        
        # Stochastic
        if latest["stoch_k"] is not None:
            if latest["stoch_k"] < 20:
                score += 15
                reasons.append(f"Stoch({latest['stoch_k']:.0f}) اشباع فروش")
            elif latest["stoch_k"] > 80:
                score -= 15
                warnings.append(f"Stoch({latest['stoch_k']:.0f}) اشباع خرید")
        
        # ═══════════════════════════════════════════════════════
        # لایه ۲: روند (MA + ADX + Ichimoku)
        # ═══════════════════════════════════════════════════════
        close = latest["price_close"]
        ma20 = latest["ma20"]
        ma50 = latest["ma50"]
        
        if close and ma20 and ma50:
            if close > ma20 > ma50:
                score += 20
                reasons.append("روند کامل (MA20 > MA50)")
            elif close < ma50:
                score -= 15
                warnings.append("زیر MA50 (نزولی)")
        
        # ADX
        adx = latest["adx14"]
        if adx is not None:
            if adx > 25:
                if latest["plus_di"] and latest["minus_di"]:
                    if latest["plus_di"] > latest["minus_di"]:
                        score += 10
                        reasons.append(f"ADX({adx:.0f}) روند صعودی قوی")
                    else:
                        score -= 10
                        warnings.append(f"ADX({adx:.0f}) روند نزولی قوی")
        
        # Ichimoku
        if latest["ichimoku_senkou_a"] and latest["ichimoku_senkou_b"]:
            cloud_top = max(latest["ichimoku_senkou_a"], latest["ichimoku_senkou_b"])
            cloud_bottom = min(latest["ichimoku_senkou_a"], latest["ichimoku_senkou_b"])
            if close > cloud_top:
                score += 10
                reasons.append("بالای ابر ایچیموکو")
            elif close < cloud_bottom:
                score -= 10
                warnings.append("زیر ابر ایچیموکو")
        
        # ═══════════════════════════════════════════════════════
        # لایه ۳: حجم و جریان پول (OBV + MFI + Volume)
        # ═══════════════════════════════════════════════════════
        if hist["avg_volume"] > 0:
            vol_ratio = latest["volume"] / hist["avg_volume"]
            if vol_ratio > 2:
                score += 15
                reasons.append(f"حجم {vol_ratio:.1f}x میانگین")
            elif vol_ratio < 0.5:
                score -= 10
                warnings.append("حجم بسیار کم")
        
        # MFI
        mfi = latest["mfi14"]
        if mfi is not None:
            if mfi < 20:
                score += 10
                reasons.append(f"MFI({mfi:.0f}) جریان پول منفی شدید")
            elif mfi > 80:
                score -= 10
                warnings.append(f"MFI({mfi:.0f}) جریان پول مثبت شدید")
        
        # ═══════════════════════════════════════════════════════
        # لایه ۴: حمایت و مقاومت (Fibonacci + Bollinger)
        # ═══════════════════════════════════════════════════════
        # Bollinger
        if latest["bb_lower"] and latest["bb_upper"]:
            if close <= latest["bb_lower"] * 1.02:
                score += 10
                reasons.append("نزدیک کف بولینگر")
            elif close >= latest["bb_upper"] * 0.98:
                score -= 10
                warnings.append("نزدیک سقف بولینگر")
        
        # موقعیت در محدوده ۵۲ هفته
        if hist["high_52w"] > hist["low_52w"]:
            position = (close - hist["low_52w"]) / (hist["high_52w"] - hist["low_52w"]) * 100
            if position > 90:
                score -= 20
                warnings.append(f"نزدیک سقف ۵۲ هفته ({position:.0f}%)")
            elif position < 20:
                score += 15
                reasons.append(f"نزدیک کف ۵۲ هفته ({position:.0f}%)")
        
        # ═══════════════════════════════════════════════════════
        # لایه ۵: فیلترهای محافظ
        # ═══════════════════════════════════════════════════════
        # رشد بیش از حد
        if hist["price_20d_ago"] > 0:
            growth = (close - hist["price_20d_ago"]) / hist["price_20d_ago"] * 100
            if growth > 30:
                score -= 25
                warnings.append(f"رشد {growth:.0f}% در ۲۰ روز (حباب)")
        
        # CCI
        cci = latest["cci20"]
        if cci is not None:
            if cci > 200:
                score -= 15
                warnings.append(f"CCI({cci:.0f}) فوق اشباع خرید")
            elif cci < -200:
                score += 10
                reasons.append(f"CCI({cci:.0f}) فوق اشباع فروش")
        
        # محدود کردن
        score = max(0, min(100, score))
        
        return {
            "ins_code": ins_code,
            "symbol": data["symbol"],
            "name": data["name"],
            "date": latest["date"],
            "close": close,
            "score": score,
            "reasons": reasons,
            "warnings": warnings,
            "rsi": round(rsi, 1) if rsi else None,
            "adx": round(adx, 1) if adx else None,
            "trend": latest["trend_direction"],
            "strength": latest["trend_strength"],
        }

    def scan_all(self, min_score=40, limit=50):
        codes = self._get_all_codes()
        results = []
        
        for code in codes:
            analysis = self.analyze(code)
            if analysis and analysis["score"] >= min_score:
                results.append(analysis)
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]


if __name__ == "__main__":
    print("=" * 70)
    print("DEEP ANALYZER - تحلیل ۵ لایه با ۳۳ اندیکاتور")
    print("=" * 70)
    
    analyzer = DeepAnalyzer()
    results = analyzer.scan_all(min_score=40, limit=30)
    analyzer.close()
    
    print(f"\nتعداد {len(results)} نماد با امتیاز >= 40:\n")
    print(f"{'#':>3} | {'نماد':12s} | {'امتیاز':>5s} | {'RSI':>6s} | {'ADX':>5s} | {'روند':>8s} | دلایل")
    print("-" * 100)
    
    for i, r in enumerate(results, 1):
        reasons = ", ".join(r["reasons"][:2])
        trend_fa = {"UP": "صعودی", "DOWN": "نزولی", "SIDEWAYS": "خنثی"}.get(r["trend"], r["trend"] or "-")
        print(f"{i:>3} | {r['symbol'][:12]:12s} | {r['score']:>5d} | {r['rsi'] or '-':>6} | {r['adx'] or '-':>5} | {trend_fa:>8s} | {reasons}")
