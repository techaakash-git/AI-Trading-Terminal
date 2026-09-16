"""Deterministic chart-pattern detection over a list of candles.

Python computes every pattern here; the LLM/frontend only renders it. Each
detected pattern is a plain dict:

    {
      "name": "double_top",              # snake_case id used for filtering
      "display": "Double Top",           # human-readable label for the UI
      "direction": "bearish",            # chart implication
      "confidence": float,               # 0..1, deterministic
      "status": "confirmed" | "forming",
      "points": [{"idx", "price", "type"}, ...],  # anchor points for markers
      "start_idx": int,
      "end_idx": int,
      "neckline": float | None,
    }
"""
from __future__ import annotations
from typing import Optional, Sequence

# Ordered so the frontend can render the Patterns dropdown in a stable order.
ALL_PATTERN_NAMES = [
    "head_and_shoulders",
    "inverse_head_and_shoulders",
    "double_top",
    "double_bottom",
    "triple_top",
    "triple_bottom",
    "ascending_triangle",
    "descending_triangle",
    "symmetrical_triangle",
    "rising_wedge",
    "falling_wedge",
]

PATTERN_DISPLAY_NAMES = {
    "head_and_shoulders": "Head & Shoulders",
    "inverse_head_and_shoulders": "Inverse Head & Shoulders",
    "double_top": "Double Top",
    "double_bottom": "Double Bottom",
    "triple_top": "Triple Top",
    "triple_bottom": "Triple Bottom",
    "ascending_triangle": "Ascending Triangle",
    "descending_triangle": "Descending Triangle",
    "symmetrical_triangle": "Symmetrical Triangle",
    "rising_wedge": "Rising Wedge",
    "falling_wedge": "Falling Wedge",
}

# Detection thresholds (deterministic, unit-tested).
TOLERANCE_PCT = 1.0          # how close two tops/bottoms must be to count as equal
MIN_RETRACEMENT_PCT = 3.0    # minimum pullback between peaks/troughs
SWING_WINDOW = 5             # fractal lookback for swing highs/lows


def _pct(a: float, b: float) -> float:
    """Percentage difference between a and b (vs. their mean)."""
    mid = (a + b) / 2
    return abs(a - b) / mid * 100 if mid else float('inf')


def _swings(candles, order=SWING_WINDOW):
    """Fractal swing points. Returns (swing_highs, swing_lows) as
    [{"idx", "price"}, ...] dicts."""
    highs, lows = [], []
    for i in range(order, len(candles) - order):
        seg_h = candles[i - order:i + order + 1]
        seg_l = candles[i - order:i + order + 1]
        if candles[i].high >= max(x.high for x in seg_h):
            highs.append({"idx": i, "price": candles[i].high})
        if candles[i].low <= min(x.low for x in seg_l):
            lows.append({"idx": i, "price": candles[i].low})
    return highs, lows


def _level_groups(points, tolerance_pct=TOLERANCE_PCT):
    """Cluster a set of (idx, price) points by near-equal price. Returns a list
    of {"top"|"bottom", "price", "idx"} clusters, price ordered ascending."""
    if not points:
        return []
    out = []
    for p in sorted(points, key=lambda x: x["price"]):
        placed = False
        for g in out:
            if _pct(g["price"], p["price"]) <= tolerance_pct:
                g["idxs"].append(p["idx"])
                g["price"] = sum(g["idxs"]) / len(g["idxs"]) if False else (g["price"] + p["price"]) / 2
                placed = True
                break
        if not placed:
            out.append({"price": p["price"], "idxs": [p["idx"]]})
    return out


def _status(candles, pattern, neckline):
    """'confirmed' if price has moved beyond the neckline after completion."""
    if neckline is None:
        return "forming"
    end = pattern["end_idx"]
    if end + 1 >= len(candles):
        return "forming"
    bearish = pattern["name"] in ("head_and_shoulders", "double_top", "triple_top")
    after_close = candles[end + 1].close
    crossed = (after_close < neckline) if bearish else (after_close > neckline)
    return "confirmed" if crossed else "forming"


def _base(name, points, neckline):
    return {
        "name": name,
        "display": PATTERN_DISPLAY_NAMES[name],
        "direction": "bearish" if name in ("head_and_shoulders", "double_top", "triple_top") else "bullish",
        "confidence": 0.8,
        "points": points,
        "start_idx": points[0]["idx"],
        "end_idx": points[-1]["idx"],
        "neckline": neckline,
    }


def detect_head_and_shoulders(highs, lows):
    found = []
    for i in range(len(highs) - 2):
        left, head, right = highs[i], highs[i + 1], highs[i + 2]
        if _pct(left["price"], right["price"]) > TOLERANCE_PCT:
            continue
        avg_shoulders = (left["price"] + right["price"]) / 2
        if head["price"] <= avg_shoulders or _pct(head["price"], avg_shoulders) < MIN_RETRACEMENT_PCT:
            continue
        trough_l = [p for p in lows if left["idx"] < p["idx"] < head["idx"]]
        trough_r = [p for p in lows if head["idx"] < p["idx"] < right["idx"]]
        if not trough_l or not trough_r:
            continue
        tl, tr = min(trough_l, key=lambda x: x["price"]), min(trough_r, key=lambda x: x["price"])
        neckline = min(tl["price"], tr["price"])
        found.append(_base("head_and_shoulders", [
            {"idx": left["idx"], "price": left["price"], "type": "high"},
            {"idx": tl["idx"], "price": tl["price"], "type": "low"},
            {"idx": head["idx"], "price": head["price"], "type": "high"},
            {"idx": tr["idx"], "price": tr["price"], "type": "low"},
            {"idx": right["idx"], "price": right["price"], "type": "high"},
        ], neckline))
    return found


def detect_inverse_head_and_shoulders(highs, lows):
    found = []
    for i in range(len(lows) - 2):
        left, head, right = lows[i], lows[i + 1], lows[i + 2]
        if _pct(left["price"], right["price"]) > TOLERANCE_PCT:
            continue
        avg_shoulders = (left["price"] + right["price"]) / 2
        if head["price"] >= avg_shoulders or _pct(head["price"], avg_shoulders) < MIN_RETRACEMENT_PCT:
            continue
        peak_l = [p for p in highs if left["idx"] < p["idx"] < head["idx"]]
        peak_r = [p for p in highs if head["idx"] < p["idx"] < right["idx"]]
        if not peak_l or not peak_r:
            continue
        pl, pr = max(peak_l, key=lambda x: x["price"]), max(peak_r, key=lambda x: x["price"])
        neckline = max(pl["price"], pr["price"])
        found.append(_base("inverse_head_and_shoulders", [
            {"idx": left["idx"], "price": left["price"], "type": "low"},
            {"idx": pl["idx"], "price": pl["price"], "type": "high"},
            {"idx": head["idx"], "price": head["price"], "type": "low"},
            {"idx": pr["idx"], "price": pr["price"], "type": "high"},
            {"idx": right["idx"], "price": right["price"], "type": "low"},
        ], neckline))
    return found


def detect_double_top(highs, lows):
    found = []
    for i in range(len(highs) - 1):
        p1, p2 = highs[i], highs[i + 1]
        if _pct(p1["price"], p2["price"]) > TOLERANCE_PCT:
            continue
        trough = [p for p in lows if p1["idx"] < p["idx"] < p2["idx"]]
        if not trough:
            continue
        t = min(trough, key=lambda x: x["price"])
        if _pct(t["price"], p1["price"]) < MIN_RETRACEMENT_PCT:
            continue
        found.append(_base("double_top", [
            {"idx": p1["idx"], "price": p1["price"], "type": "high"},
            {"idx": t["idx"], "price": t["price"], "type": "low"},
            {"idx": p2["idx"], "price": p2["price"], "type": "high"},
        ], t["price"]))
    return found


def detect_double_bottom(highs, lows):
    found = []
    for i in range(len(lows) - 1):
        p1, p2 = lows[i], lows[i + 1]
        if _pct(p1["price"], p2["price"]) > TOLERANCE_PCT:
            continue
        peak = [p for p in highs if p1["idx"] < p["idx"] < p2["idx"]]
        if not peak:
            continue
        pk = max(peak, key=lambda x: x["price"])
        if _pct(pk["price"], p1["price"]) < MIN_RETRACEMENT_PCT:
            continue
        found.append(_base("double_bottom", [
            {"idx": p1["idx"], "price": p1["price"], "type": "low"},
            {"idx": pk["idx"], "price": pk["price"], "type": "high"},
            {"idx": p2["idx"], "price": p2["price"], "type": "low"},
        ], pk["price"]))
    return found


def detect_triple_top(highs, lows):
    found = []
    for i in range(len(highs) - 2):
        p1, p2, p3 = highs[i], highs[i + 1], highs[i + 2]
        if _pct(p1["price"], p2["price"]) > TOLERANCE_PCT or _pct(p2["price"], p3["price"]) > TOLERANCE_PCT:
            continue
        trough_a = [p for p in lows if p1["idx"] < p["idx"] < p2["idx"]]
        trough_b = [p for p in lows if p2["idx"] < p["idx"] < p3["idx"]]
        if not trough_a or not trough_b:
            continue
        ta, tb = min(trough_a, key=lambda x: x["price"]), min(trough_b, key=lambda x: x["price"])
        if _pct(ta["price"], p1["price"]) < MIN_RETRACEMENT_PCT or _pct(tb["price"], p2["price"]) < MIN_RETRACEMENT_PCT:
            continue
        found.append(_base("triple_top", [
            {"idx": p1["idx"], "price": p1["price"], "type": "high"},
            {"idx": ta["idx"], "price": ta["price"], "type": "low"},
            {"idx": p2["idx"], "price": p2["price"], "type": "high"},
            {"idx": tb["idx"], "price": tb["price"], "type": "low"},
            {"idx": p3["idx"], "price": p3["price"], "type": "high"},
        ], min(ta["price"], tb["price"])))
    return found


def detect_triple_bottom(highs, lows):
    found = []
    for i in range(len(lows) - 2):
        p1, p2, p3 = lows[i], lows[i + 1], lows[i + 2]
        if _pct(p1["price"], p2["price"]) > TOLERANCE_PCT or _pct(p2["price"], p3["price"]) > TOLERANCE_PCT:
            continue
        peak_a = [p for p in highs if p1["idx"] < p["idx"] < p2["idx"]]
        peak_b = [p for p in highs if p2["idx"] < p["idx"] < p3["idx"]]
        if not peak_a or not peak_b:
            continue
        pa, pb = max(peak_a, key=lambda x: x["price"]), max(peak_b, key=lambda x: x["price"])
        if _pct(pa["price"], p1["price"]) < MIN_RETRACEMENT_PCT or _pct(pb["price"], p2["price"]) < MIN_RETRACEMENT_PCT:
            continue
        found.append(_base("triple_bottom", [
            {"idx": p1["idx"], "price": p1["price"], "type": "low"},
            {"idx": pa["idx"], "price": pa["price"], "type": "high"},
            {"idx": p2["idx"], "price": p2["price"], "type": "low"},
            {"idx": pb["idx"], "price": pb["price"], "type": "high"},
            {"idx": p3["idx"], "price": p3["price"], "type": "low"},
        ], max(pa["price"], pb["price"])))
    return found


def _is_seq_rising(seq, min_pct):
    if len(seq) < 2 or any(seq[i] >= seq[i + 1] for i in range(len(seq) - 1)):
        return False
    return (seq[-1] - seq[0]) / seq[0] * 100 >= min_pct if seq[0] else False


def _is_seq_falling(seq, min_pct):
    if len(seq) < 2 or any(seq[i] <= seq[i + 1] for i in range(len(seq) - 1)):
        return False
    return (seq[0] - seq[-1]) / seq[0] * 100 >= min_pct if seq[0] else False


def detect_triangle_or_wedge(highs, lows, lookback=4):
    """Classify the most recent triangle/wedge from recent swing points."""
    if len(highs) < 2 or len(lows) < 2:
        return None
    r_high = highs[-lookback:]
    r_low = lows[-lookback:]
    hp = [p["price"] for p in r_high]
    lp = [p["price"] for p in r_low]
    h_flat = (max(hp) - min(hp)) / min(hp) * 100 <= TOLERANCE_PCT if min(hp) else False
    l_flat = (max(lp) - min(lp)) / min(lp) * 100 <= TOLERANCE_PCT if min(lp) else False
    h_rising, h_falling = _is_seq_rising(hp, MIN_RETRACEMENT_PCT), _is_seq_falling(hp, MIN_RETRACEMENT_PCT)
    l_rising, l_falling = _is_seq_rising(lp, MIN_RETRACEMENT_PCT), _is_seq_falling(lp, MIN_RETRACEMENT_PCT)

    points = ([{"idx": p["idx"], "price": p["price"], "type": "high"} for p in r_high]
              + [{"idx": p["idx"], "price": p["price"], "type": "low"} for p in r_low])
    points.sort(key=lambda p: p["idx"])
    start_idx = min(r_high[0]["idx"], r_low[0]["idx"])
    end_idx = max(r_high[-1]["idx"], r_low[-1]["idx"])

    def build(name, direction, conf):
        return {
            "name": name,
            "display": PATTERN_DISPLAY_NAMES[name],
            "direction": direction,
            "confidence": conf,
            "status": "forming",
            "points": points,
            "start_idx": start_idx,
            "end_idx": end_idx,
            "neckline": None,
        }

    if h_flat and l_rising:
        return build("ascending_triangle", "bullish", 0.7)
    if h_falling and l_flat:
        return build("descending_triangle", "bearish", 0.7)
    if h_falling and l_rising:
        return build("symmetrical_triangle", "bullish", 0.6)

    first_range = abs(r_high[0]["price"] - r_low[0]["price"])
    last_range = abs(r_high[-1]["price"] - r_low[-1]["price"])
    narrowing = last_range < first_range
    if h_rising and l_rising and narrowing:
        return build("rising_wedge", "bearish", 0.65)
    if h_falling and l_falling and narrowing:
        return build("falling_wedge", "bullish", 0.65)
    return None


def _pattern_span(pattern) -> tuple[int, int]:
    """Inclusive (start, end) candle-index span of a pattern's anchor points."""
    idxs = [pt["idx"] for pt in pattern["points"]]
    return min(idxs), max(idxs)


def _shared_anchors(a, b) -> int:
    """How many swing anchor *levels* two patterns share.

    Two points count as the same level if they have the same `type` (high vs
    low) and are within ``TOLERANCE_PCT`` of each other.  This is important
    because flat peaks/troughs produce duplicate swings at adjacent indices
    that are semantically the same structural point.
    """
    count = 0
    for pa in a["points"]:
        for pb in b["points"]:
            if pa["type"] == pb["type"] and _pct(pa["price"], pb["price"]) <= TOLERANCE_PCT:
                count += 1
                break  # each point in *a* matches at most once
    return count


def _resolve_pattern_conflicts(patterns) -> list:
    """Post-process detection results so the UI never shows a pattern salad:

    1. Nested same-direction collapse — a double_bottom that sits entirely
       inside a triple_bottom (or a double_top inside a triple_top) is a
       subset of the same structure; only the larger one is reported.
    2. Cross-direction conflict — on a range-bound market the same swing
       highs/lows can satisfy both a top-family and a bottom-family pattern
       at once (three near-equal highs AND three near-equal lows). Presenting
       both is contradictory, so where two opposite-direction patterns share
       >= 2 swing anchors the stronger one wins:
         - a confirmed pattern beats a still-forming one;
         - otherwise the most recent (largest end_idx) wins.

    The result is deterministic and still ordered by end_idx descending.
    """
    collapses = []
    for p in patterns:
        s, e = _pattern_span(p)
        if any(
            q["direction"] == p["direction"]
            and q["start_idx"] <= s
            and e <= q["end_idx"]
            and (q["start_idx"], q["end_idx"]) != (s, e)
            for q in patterns
        ):
            continue  # nested duplicate of a bigger same-direction pattern
        collapses.append(p)

    resolved: list = []
    for p in sorted(collapses, key=lambda x: -x["end_idx"]):
        rivals = [
            q for q in resolved
            if q["direction"] != p["direction"] and _shared_anchors(q, p) >= 2
        ]
        if not rivals:
            resolved.append(p)
            continue
        # p (newest) may displace a rival unless that rival is confirmed while
        # p is only forming; process everything the rival set would evict.
        displaced = False
        for r in rivals:
            if r["status"] == "confirmed" and p["status"] != "confirmed":
                continue  # the confirmed rival keeps its place
            resolved.remove(r)
            displaced = True
        if displaced or p["status"] == "confirmed":
            resolved.append(p)
    return sorted(resolved, key=lambda x: -x["end_idx"])


def detect_patterns(candles, enabled_patterns: Optional[Sequence[str]] = None):
    """Detect chart patterns over a list of candle objects.

    ``enabled_patterns`` optionally restricts detection to a subset of
    ALL_PATTERN_NAMES (the Patterns dropdown filter). Returns a list of pattern
    dicts, sorted by recency (end_idx descending)."""
    if not candles or len(candles) < 40:
        return []
    highs, lows = _swings(candles)
    if not highs or not lows:
        return []

    enabled = set(enabled_patterns) if enabled_patterns is not None else set(ALL_PATTERN_NAMES)
    found = []
    if "head_and_shoulders" in enabled:
        found += detect_head_and_shoulders(highs, lows)
    if "inverse_head_and_shoulders" in enabled:
        found += detect_inverse_head_and_shoulders(highs, lows)
    if "double_top" in enabled:
        found += detect_double_top(highs, lows)
    if "double_bottom" in enabled:
        found += detect_double_bottom(highs, lows)
    if "triple_top" in enabled:
        found += detect_triple_top(highs, lows)
    if "triple_bottom" in enabled:
        found += detect_triple_bottom(highs, lows)

    tri_enabled = enabled & {"ascending_triangle", "descending_triangle", "symmetrical_triangle", "rising_wedge", "falling_wedge"}
    if tri_enabled:
        tri = detect_triangle_or_wedge(highs, lows)
        if tri and tri["name"] in tri_enabled:
            found.append(tri)

    for p in found:
        p["status"] = _status(candles, p, p["neckline"])

    found = _resolve_pattern_conflicts(found)
    return found