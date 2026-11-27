def compute_pivot_points(high, low, close):
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low; r2 = pivot + (high - low); r3 = high + 2 * (pivot - low)
    s1 = 2 * pivot - high; s2 = pivot - (high - low); s3 = low - 2 * (high - pivot)
    return {"pivot": pivot, "r1": r1, "r2": r2, "r3": r3, "s1": s1, "s2": s2, "s3": s3}

def compute_pivot_fibonacci(high, low, close):
    pivot = (high + low + close) / 3; rng = high - low
    r1 = pivot + 0.382 * rng; r2 = pivot + 0.618 * rng; r3 = pivot + 1.000 * rng
    s1 = pivot - 0.382 * rng; s2 = pivot - 0.618 * rng; s3 = pivot - 1.000 * rng
    return {"pivot": pivot, "r1": r1, "r2": r2, "r3": r3, "s1": s1, "s2": s2, "s3": s3}
