def compute_supertrend(prices, atr_list, multiplier=3.0):
    n = len(prices); st=[None]*n; dir=[None]*n; up=[None]*n; lo=[None]*n
    for i in range(n):
        if atr_list[i] is None: continue
        hl2 = (prices[i]["price_max"] + prices[i]["price_min"]) / 2
        u = hl2 + multiplier*atr_list[i]; l = hl2 - multiplier*atr_list[i]
        up[i]=u; lo[i]=l
        if i == 0 or st[i-1] is None: st[i]=l; dir[i]="UP"; continue
        prev_st=st[i-1]; prev_dir=dir[i-1]
        if prev_dir == "UP":
            if prices[i]["price_close"] < prev_st: st[i]=u; dir[i]="DOWN"
            else: st[i]=max(l, prev_st); dir[i]="UP"
        else:
            if prices[i]["price_close"] > prev_st: st[i]=l; dir[i]="UP"
            else: st[i]=min(u, prev_st); dir[i]="DOWN"
    return {"supertrend":st, "direction":dir, "upper":up, "lower":lo}

def compute_rvol(prices, period=20):
    n=len(prices); r=[None]*n
    for i in range(period, n):
        avg = sum(prices[j]["volume"] for j in range(i-period, i)) / period
        if avg > 0: r[i] = prices[i]["volume"] / avg
    return r

def compute_stoch_rsi(rsi_list, period=14):
    n=len(rsi_list); sr=[None]*n
    for i in range(period-1, n):
        w = [rsi_list[j] for j in range(i-period+1, i+1) if rsi_list[j] is not None]
        if len(w) < period: continue
        h=max(w); l=min(w)
        if h-l > 0: sr[i] = 100*(rsi_list[i]-l)/(h-l)
    return sr

def compute_wma(prices, period=20):
    n=len(prices); r=[None]*n
    w=list(range(1, period+1)); ws=sum(w)
    for i in range(period-1, n):
        vals = [prices[j]["price_close"] for j in range(i-period+1, i+1)]
        r[i] = sum(a*b for a,b in zip(w, vals)) / ws
    return r

def compute_vwma(prices, period=20):
    n=len(prices); r=[None]*n
    for i in range(period-1, n):
        pv = sum(prices[j]["price_close"]*prices[j]["volume"] for j in range(i-period+1, i+1))
        v = sum(prices[j]["volume"] for j in range(i-period+1, i+1))
        if v > 0: r[i] = pv/v
    return r

def compute_aroon(prices, period=25):
    n=len(prices); up=[None]*n; dn=[None]*n; osc=[None]*n
    for i in range(period, n):
        w = [prices[j]["price_close"] for j in range(i-period, i+1)]
        hi_idx = w.index(max(w)); lo_idx = w.index(min(w))
        up[i] = (period - (period - hi_idx)) / period * 100
        dn[i] = (period - (period - lo_idx)) / period * 100
        osc[i] = up[i] - dn[i]
    return {"aroon_up":up, "aroon_down":dn, "aroon_osc":osc}
