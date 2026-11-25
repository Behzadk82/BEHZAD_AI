# src/analysis/smart_scanner.py
# موتور جستجوی خودکار با ۷ استراتژی + ۴ فیلتر محافظ (Risk Filters)

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DB_PATH

class SmartScanner:
    def __init__(self):
        self.con = sqlite3.connect(DB_PATH, timeout=15)
        self.con.row_factory = sqlite3.Row

    def close(self):
        if self.con: self.con.close()

    def _get_all_codes(self):
        return [r["ins_code"] for r in self.con.execute("SELECT DISTINCT ins_code FROM indicators").fetchall()]

    def _get_history(self, ins_code, limit=260):
        # ۲۶۰ روز معاملاتی حدوداً معادل یک سال است (برای محاسبه سقف سالانه)
        rows = self.con.execute("""
            SELECT p.date, p.price_close, p.volume,
                   i.ma5, i.ma20, i.ma50, i.rsi14,
                   i.macd, i.macd_signal, i.bb_upper, i.bb_lower
            FROM price_history p
            JOIN indicators i ON p.ins_code = i.ins_code AND p.date = i.date
            WHERE p.ins_code = ?
            ORDER BY p.date DESC LIMIT ?
        """, (ins_code, limit)).fetchall()
        
        sym = self.con.execute("SELECT symbol, name FROM symbols WHERE ins_code = ?", (ins_code,)).fetchone()
        if not rows or not sym: return None
        
        return {
            "symbol": sym["symbol"], 
            "name": sym["name"],
            "rows": [dict(r) for r in reversed(rows)]
        }

    def scan(self, min_score=30):
        codes = self._get_all_codes()
        results = []
        
        for code in codes:
            data = self._get_history(code)
            if not data or len(data["rows"]) < 30: continue
            
            rows = data["rows"]
            last = rows[-1]
            prev = rows[-2]
            
            # --- بررسی اینکه قیمت چقدر از سقف یک ساله فاصله داره ---
            year_high = max(r["price_close"] for r in rows)
            price_near_high = (last["price_close"] / year_high) >= 0.95 if year_high else False
            
            score = 0
            reasons = []
            
            # ==========================================
            # بخش اول: امتیازهای مثبت (استراتژی‌ها)
            # ==========================================
            
            # ۱. مومنتوم ترکیبی
            if last["rsi14"] and last["macd"] and last["macd_signal"]:
                if last["rsi14"] < 35 and last["macd"] > last["macd_signal"]:
                    score += 30
                    reasons.append(f"RSI({last['rsi14']:.0f}) + MACD صعودی")
                elif last["rsi14"] < 45 and last["macd"] > last["macd_signal"]:
                    score += 15
                    reasons.append(f"RSI({last['rsi14']:.0f}) + MACD صعودی")

            # ۲. روند صعودی
            if last["ma20"] and last["ma50"]:
                if last["price_close"] > last["ma20"] > last["ma50"]:
                    score += 25
                    reasons.append("روند کامل (MA20 > MA50)")
                elif last["price_close"] > last["ma50"]:
                    score += 10
                    reasons.append("بالای MA50")

            # ۳. انفجار قیمتی
            if last["bb_upper"] and last["bb_lower"]:
                bb_width = (last["bb_upper"] - last["bb_lower"]) / last["price_close"]
                avg_vol = sum(r["volume"] for r in rows[-20:]) / 20
                if bb_width < 0.15 and last["volume"] > avg_vol * 1.5:
                    score += 20
                    reasons.append("فشردگی بولینگر + حجم")

            # ۴. برگشت از حمایت
            if last["bb_lower"] and last["rsi14"]:
                if last["price_close"] <= last["bb_lower"] * 1.02 and last["rsi14"] < 40:
                    score += 20
                    reasons.append("برگشت از حمایت (نزدیک کف)")

            # ۵. کراس طلایی MACD
            if last["macd"] and last["macd_signal"] and prev["macd"] and prev["macd_signal"]:
                if prev["macd"] <= prev["macd_signal"] and last["macd"] > last["macd_signal"]:
                    score += 25
                    reasons.append("کراس طلایی MACD")

            # ۶. کراس MA
            if last["ma5"] and last["ma20"] and prev["ma5"] and prev["ma20"]:
                if prev["ma5"] <= prev["ma20"] and last["ma5"] > last["ma20"]:
                    score += 25
                    reasons.append("کراس طلایی MA5/MA20")

            # ۷. حجم غیرعادی
            avg_vol_19 = sum(r["volume"] for r in rows[-20:-1]) / 19
            if avg_vol_19 > 0 and last["volume"] > avg_vol_19 * 2:
                score += 15
                reasons.append(f"حجم {last['volume']/avg_vol_19:.1f}x")

            # ==========================================
            # بخش دوم: فیلترهای محافظ (Risk Filters)
            # ==========================================
            
            # فیلتر ۱: نزدیک سقف یک ساله (خطر اصلاح)
            if price_near_high:
                score -= 30
                reasons.append("⚠️ نزدیک سقف سالانه")

            # فیلتر ۲: RSI خیلی بالا (اشباع خرید)
            if last["rsi14"] and last["rsi14"] > 75:
                score -= 25
                reasons.append("⚠️ RSI اشباع خرید")
            elif last["rsi14"] and last["rsi14"] > 70:
                score -= 15
                reasons.append("⚠️ RSI بالا")

            # فیلتر ۳: رشد بیش از حد در ۲۰ روز
            if len(rows) >= 20:
                price_20d_ago = rows[-20]["price_close"]
                if price_20d_ago > 0:
                    growth = (last["price_close"] - price_20d_ago) / price_20d_ago * 100
                    if growth > 40:
                        score -= 25
                        reasons.append(f"⚠️ رشد {growth:.0f}% در ۲۰ روز")

            # فیلتر ۴: فاصله از MA20
            if last["ma20"] and last["price_close"]:
                gap = (last["price_close"] - last["ma20"]) / last["ma20"] * 100
                if gap > 25:
                    score -= 20
                    reasons.append(f"⚠️ {gap:.0f}% بالای MA20")

            score = max(0, min(100, score))

            if score >= min_score:
                results.append({
                    "ins_code": code,
                    "symbol": data["symbol"],
                    "name": data["name"],
                    "close": last["price_close"],
                    "score": score,
                    "reasons": reasons,
                    "rsi": round(last["rsi14"], 1) if last["rsi14"] else None,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results
