def compute_volume_profile(prices, days=60, bins=10):
    if len(prices) < days: days = len(prices)
    recent = prices[-days:]
    highs = [p["price_max"] for p in recent]; lows = [p["price_min"] for p in recent]
    if not highs or not lows: return None
    price_min = min(lows); price_max = max(highs)
    if price_max <= price_min: return None
    bin_size = (price_max - price_min) / bins
    profile = [0.0] * bins
    for p in recent:
        mid = (p["price_max"] + p["price_min"]) / 2
        idx = min(int((mid - price_min) / bin_size), bins - 1)
        profile[idx] += p["volume"]
    poc_idx = profile.index(max(profile))
    poc_price = price_min + (poc_idx + 0.5) * bin_size
    total_vol = sum(profile); sorted_profile = sorted(enumerate(profile), key=lambda x: x[1], reverse=True)
    cum = 0; va_indices = []
    for i, v in sorted_profile:
        cum += v; va_indices.append(i)
        if cum >= total_vol * 0.7: break
    va_low = price_min + min(va_indices) * bin_size; va_high = price_min + (max(va_indices) + 1) * bin_size
    return {"poc": poc_price, "value_area_low": va_low, "value_area_high": va_high}

def compute_support_resistance(prices, lookback=50, num_levels=3):
    if len(prices) < lookback: lookback = len(prices)
    recent = prices[-lookback:]
    highs = [p["price_max"] for p in recent]; lows = [p["price_min"] for p in recent]
    current = prices[-1]["price_close"]
    resistances = sorted(set(highs), reverse=True)[:num_levels]; supports = sorted(set(lows))[:num_levels]
    nearest_res = next((r for r in resistances if r > current), None)
    nearest_sup = next((s for s in reversed(supports) if s < current), None)
    return {"supports": supports, "resistances": resistances, "nearest_support": nearest_sup, "nearest_resistance": nearest_res, "current": current}
