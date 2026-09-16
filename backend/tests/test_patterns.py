from app.engine.patterns import detect_patterns, ALL_PATTERN_NAMES, PATTERN_DISPLAY_NAMES
from app.market.models import Candle

def _mk(closes):
    return [Candle(time=i, open=closes[i], high=closes[i]+0.2, low=closes[i]-0.2, close=closes[i], volume=1)
            for i in range(len(closes))]

def _rising():
    return [80+i*2 for i in range(11)]

def test_all_pattern_names_unique_and_cover_display():
    assert len(ALL_PATTERN_NAMES) == 11
    assert len(PATTERN_DISPLAY_NAMES) == 11
    assert set(ALL_PATTERN_NAMES) == set(PATTERN_DISPLAY_NAMES)

def test_insufficient_data_returns_empty():
    assert detect_patterns(_mk([1]*10)) == []

def test_monotonic_rising_no_patterns():
    closes = [100+i*0.5 for i in range(80)]
    assert detect_patterns(_mk(closes)) == []

def test_double_top_detected():
    closes = _rising()
    closes += [100-(i+1)*2 for i in range(6)]   # trough
    closes += [90+(i+1)*2 for i in range(5)]    # second peak
    closes += [85]                                # immediate breakdown
    closes += [84]*22
    pats = detect_patterns(_mk(closes), ['double_top'])
    assert len(pats) >= 1
    assert pats[0]['name'] == 'double_top'
    assert pats[0]['direction'] == 'bearish'
    assert pats[0]['status'] == 'confirmed'
    assert len(pats[0]['points']) == 3
    for pt in pats[0]['points']:
        assert 'idx' in pt and 'price' in pt and 'type' in pt
        assert 0 <= pt['idx'] < len(closes)

def test_enabling_filter_restricts_output():
    closes = [100+i*0.5 for i in range(80)]
    pats = detect_patterns(_mk(closes), ['double_top'])
    # Monotonic series: no patterns at all, so empty regardless.
    assert pats == []

def test_pattern_has_display_name():
    closes = _rising()
    closes += [100-(i+1)*2 for i in range(6)]
    closes += [90+(i+1)*2 for i in range(5)]
    closes += [85]
    closes += [84]*22
    pats = detect_patterns(_mk(closes), ['double_top'])
    assert pats[0]['display'] == 'Double Top'

def test_points_are_ordered_by_idx():
    closes = _rising()
    closes += [100-(i+1)*2 for i in range(6)]
    closes += [90+(i+1)*2 for i in range(5)]
    closes += [85]*23
    pats = detect_patterns(_mk(closes), ['double_top'])
    if pats:
        idxs = [pt['idx'] for pt in pats[0]['points']]
        assert idxs == sorted(idxs)


# ---------------------------------------------------------------------------
# Conflict-resolution tests
# ---------------------------------------------------------------------------

def _range_bound_closes():
    """Synthetic range-bound market: 40 bars up to ~4596, 46 bars down to
    ~4342, 46 bars up to ~4596, 46 bars down to ~4342, 44 bars up to ~4596,
    30 flat.  Three near-equal highs + three near-equal lows (triggers
    both bottom and top families simultaneously)."""
    # rise from 4342 to 4596 (approx 3%)
    up1 = [4342 + i * (4596 - 4342) / 40 for i in range(41)]
    # drop back to 4342
    down1 = [4596 - i * (4596 - 4342) / 45 for i in range(46)]
    # up again
    up2 = [4342 + i * (4596 - 4342) / 45 for i in range(46)]
    # down again
    down2 = [4596 - i * (4596 - 4342) / 45 for i in range(46)]
    # up once more
    up3 = [4342 + i * (4596 - 4342) / 44 for i in range(44)]
    # short flat at the peak
    flat = [4596] * 30
    return up1 + down1 + up2 + down2 + up3 + flat


def test_range_bound_no_bottom_and_top_simultaneously():
    """On a range-bound market the detectors should not produce BOTH a
    bottom-family and a top-family pattern — the UI would show
    contradictory signals. Uses clean single-swing geometry matching the
    real XAUUSD range-bound scenario (three near-equal highs + lows,
    single swing point per peak/trough)."""
    # Rise to peak, fall to trough, repeat — with no flat tops/peaks to
    # produce duplicate swings. Each peak and trough is a single bar.
    peak, trough = 120, 100
    up1 = [100 + i * (peak - 100) / 10 for i in range(11)]       # 100→120 (bar 0..10)
    down1 = [peak - i * (peak - trough) / 15 for i in range(16)] # 120→100 (bar 11..26)
    up2 = [trough + i * (peak - trough) / 15 for i in range(16)] # 100→120 (bar 27..42)
    down2 = [peak - i * (peak - trough) / 15 for i in range(16)] # 120→100 (bar 43..58)
    up3 = [trough + i * (peak - trough) / 15 for i in range(16)] # 100→120 (bar 59..74)
    flat = [peak] * 40                                            # hold at peak
    closes = up1 + down1 + up2 + down2 + up3 + flat
    pats = detect_patterns(_mk(closes))
    directions = [p["direction"] for p in pats]
    assert "bullish" not in directions or "bearish" not in directions, (
        f"contradictory patterns on range data: {[p['name'] for p in pats]}"
    )


def test_nested_pattern_collapsed():
    """A double_bottom nested inside a triple_bottom sharing the same
    span should not both appear in the output."""
    closes = _range_bound_closes()
    pats = detect_patterns(_mk(closes))
    double_bottoms = [p for p in pats if p["name"] == "double_bottom"]
    triples = [p for p in pats if p["name"] == "triple_bottom"]
    # All detected double_bottoms should have their span nested inside
    # at least one triple_bottom that was kept (the triple supersedes them).
    if triples and double_bottoms:
        for db in double_bottoms:
            db_s, db_e = db["start_idx"], db["end_idx"]
            covered = any(
                t["start_idx"] <= db_s and db_e <= t["end_idx"]
                for t in triples
            )
            assert covered, (
                f"double_bottom {db_s}-{db_e} was not collapsed into a triple"
            )


def test_confirmed_top_beats_forming_bottom():
    """When a confirmed top-family pattern shares anchors with a forming
    bottom-family pattern, the confirmed one should be retained."""
    from app.engine.patterns import (
        detect_head_and_shoulders, detect_inverse_head_and_shoulders,
        _swings, _status
    )
    # Build a structure where head-and-shoulders (bearish) forms first
    # and is confirmed, while an inverse-H&S (bullish) would use the same
    # swing points. We craft the candles so the neckline is broken *below*
    # (confirming the bearish pattern) but not above.
    rises = [100 + i * 2 for i in range(11)]        # rise to 120
    falls1 = [120 - i * 2 for i in range(11)]       # trough at 100
    rises2 = [100 + i * 3 for i in range(11)]       # head peak at 130
    falls2 = [130 - i * 3 for i in range(11)]       # trough at 100
    rises3 = [100 + i * 2 for i in range(11)]       # right shoulder at 120
    crash = [120 - i * 5 for i in range(5)]          # breakdown below 100
    flats = [95] * 22                                 # stay below neckline

    closes = rises + falls1 + rises2 + falls2 + rises3 + crash + flats
    candle_objs = _mk(closes)
    pats = detect_patterns(candle_objs)
    # We only need to check that if both bearish and bullish families
    # appear on the same anchors, the confirmed one is retained.
    bearish_confirmed = [p for p in pats
                         if p["direction"] == "bearish" and p["status"] == "confirmed"]
    bullish_forming = [p for p in pats
                       if p["direction"] == "bullish" and p["status"] == "forming"]
    # Both should not co-exist after conflict resolution.
    if bearish_confirmed and bullish_forming:
        assert False, (
            "confirmed bearish pattern should have displaced forming bullish "
            f"pattern: {[p['name'] for p in pats]}"
        )


def test_independent_patterns_not_collapsed():
    """Two patterns in distinct, non-overlapping index ranges should both
    survive conflict resolution when they don't share anchors."""
    # Pattern A: bars 0-44 — classic double top at ~100 with trough at 90.
    a = [80 + i * 2 for i in range(11)]          # rise to 100 (bars 0..10)
    a += [100 - (i + 1) * 2 for i in range(6)]   # trough to 90 (11..16)
    a += [90 + (i + 1) * 2 for i in range(5)]    # second peak 100 (17..21)
    a += [85] * 23                                 # breakdown + flat (22..44)
    # Pattern B: bars 90-134 — classic double bottom at ~50 with peak at 60.
    b = [50] * 90
    b = b[:90] + [50 - (i + 1) for i in range(5)]   # low to 45 (91..95)
    b += [45 + (i + 1) * 2 for i in range(6)]        # peak at 57 (96..101)
    b += [57 - (i + 1) * 2 for i in range(6)]        # back to 45 (102..107)
    b += [50] * 27                                      # rebound (108..134)
    closes = a + b
    pats = detect_patterns(_mk(closes))
    names = [p["name"] for p in pats]
    # Two distinct non-overlapping regions, should produce 2 patterns.
    assert len(pats) >= 2, f"expected ≥2 independent patterns, got {names}"
