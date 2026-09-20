"""Phase 15 — market regime detection tests (deterministic labels).

The fixtures keep ATR consistent with the candles they describe: a candle with
high=close+2 and low=close-2 has a true range of 4.0, so its rolling ATR is 4.0.
Callers always pass indicators computed from the same candles, so tests respect
that invariant (never fabricate a mismatched current ATR).
"""
from app.engine.regimes import detect_regime
from app.market.models import Candle

# True range of a candle opened/closed flat with high=+2, low=-2 is 4.0.
FLAT_ATR = 4.0


def _candles(n=220, close=100.0, range_size=2.0):
    return [
        Candle(time=i, open=close, high=close + range_size, low=close - range_size,
               close=close, volume=100.0)
        for i in range(n)
    ]


def _ind(trend='bullish', atr=FLAT_ATR, ema50=98.0):
    """indicator snapshot consistent with _candles(); ATR defaults to 4.0."""
    return {'trend': trend, 'atr14': atr, 'ema50': ema50}


def _atr_series_value():
    """Compute the actual last ATR for the fixtures (4.0 for range_size=2)."""
    from app.engine.indicators import atr
    c = _candles()
    s = atr([x.high for x in c], [x.low for x in c], [x.close for x in c], 14)
    return [v for v in s if v is not None][-1]


def test_bullish_regime_label():
    r = detect_regime(_candles(), _ind(trend='bullish'))
    assert r['trend'] == 'bullish'
    assert r['regime_label'].startswith('bullish_')


def test_bearish_regime_label():
    r = detect_regime(_candles(), _ind(trend='bearish'))
    assert r['trend'] == 'bearish'
    # atr=4.0 == every trailing ATR -> tie credit -> 50% -> medium.
    assert r['regime_label'] == 'bearish_medium'


def test_neutral_regime():
    r = detect_regime(_candles(), _ind(trend='neutral'))
    assert r['trend'] == 'neutral'


def test_high_volatility_label():
    # Constant history ATR=4.0; current ATR=5.5 beats all of it -> 100th pct.
    r = detect_regime(_candles(), _ind(atr=5.5))
    assert r['volatility'] == 'high'
    assert r['atr_percentile'] >= 75.0


def test_low_volatility_label():
    r = detect_regime(_candles(), _ind(atr=3.0))
    assert r['volatility'] == 'low'
    assert r['atr_percentile'] <= 25.0


def test_medium_volatility_label():
    # Current ATR exactly equals the constant trailing ATR -> 50% (tie-aware).
    r = detect_regime(_candles(), _ind(atr=FLAT_ATR))
    assert r['volatility'] == 'medium'
    assert abs(r['atr_percentile'] - 50.0) < 1.0


def test_atr_series_value_consistent_with_fixture():
    # Guards the fixture invariant: the last rolling ATR equals FLAT_ATR=4.0.
    assert _atr_series_value() == FLAT_ATR


def test_trend_strength_from_ema50_distance():
    r = detect_regime(_candles(close=100.0), _ind(ema50=90.0))
    assert r['trend_strength'] == round((100 - 90) / 90 * 100, 4)


def test_empty_candles_never_crashes():
    r = detect_regime([], {'trend': 'neutral', 'atr14': None, 'ema50': None})
    assert r['volatility'] == 'low'


def test_regime_is_deterministic():
    candles = _candles()
    a = detect_regime(candles, _ind(atr=2.0))
    b = detect_regime(candles, _ind(atr=2.0))
    assert a == b