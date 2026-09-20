"""Phase 15 — Deterministic feature engineering.

Pure, dependency-free functions that turn raw candles + pre-computed indicators
into a flat, ML-ready feature vector. Every feature is a scalar; no NaN/Inf ever
leaves this module. No forward-looking data: only the latest candle and the
already-computed indicator snapshots are used.
"""
from __future__ import annotations

import math

_TREND_ENCODE = {'bullish': 1.0, 'neutral': 0.0, 'bearish': -1.0}


def _safe(value):
    """Coerce any non-finite value to 0.0 so JSON / ML never see NaN/Inf."""
    if value is None:
        return 0.0
    value = float(value)
    return value if math.isfinite(value) else 0.0


def _pct_change(now, then, fallback=0.0):
    if then is None or then == 0:
        return fallback
    val = (now - then) / then * 100.0
    return val if math.isfinite(val) else fallback


def calculate_features(candles: list, indicators: dict) -> dict:
    """Extract a flat feature vector from candles + an indicators snapshot.

    All feature names are snake_case floats. A ``_degraded`` boolean flags any
    feature that could not be computed due to insufficient data, so callers can
    drop the row from ML training rather than silently trusting zeros.
    """
    if not candles:
        return {'_degraded': True}

    closes = [c.close for c in candles]
    price = closes[-1]
    degraded = False

    # Price returns (%) over 1 / 5 / 20 bars.
    def _return(bars):
        if len(closes) <= bars:
            return 0.0, True
        val = _pct_change(price, closes[-1 - bars])
        return val, not math.isfinite(val)

    r1, d1 = _return(1)
    r5, d5 = _return(5)
    r20, d20 = _return(20)
    degraded = degraded or d1 or d5 or d20

    # EMA distance (%): how far price sits from trend anchors.
    ema20 = indicators.get('ema20')
    ema50 = indicators.get('ema50')
    degraded = degraded or ema20 is None or ema50 is None
    ema_distance_20 = _pct_change(price, ema20) if ema20 else 0.0
    ema_distance_50 = _pct_change(price, ema50) if ema50 else 0.0

    # Normalized oscillators.
    rsi = indicators.get('rsi14')
    rsi_norm = _safe(rsi) / 100.0
    macd_hist = indicators.get('macd_histogram')
    macd_hist_norm = (macd_hist / price * 100.0) if (macd_hist is not None and price) else 0.0
    atr = indicators.get('atr14')
    atr_pct = (atr / price * 100.0) if (atr is not None and price) else 0.0

    # Volume ratio: latest volume vs simple average of last 20.
    volume_ratio = 0.0
    vols = [c.volume for c in candles]
    if len(vols) > 20 and any(v != 0 for v in vols[-21:]):
        avg = sum(vols[-21:-1]) / 20.0
        if avg > 0:
            volume_ratio = _safe(vols[-1] / avg)

    # Trend, encoded for ML.
    trend = indicators.get('trend', 'neutral')
    trend_encoded = _TREND_ENCODE.get(trend, 0.0)

    # ATR percentile vs the last 200 candles -> volatility regime rank (0-100).
    atr_percentile = _atr_percentile(candles, indicators.get('atr14'))

    return {
        'returns_1': round(_safe(r1), 6),
        'returns_5': round(_safe(r5), 6),
        'returns_20': round(_safe(r20), 6),
        'ema_distance_20': round(_safe(ema_distance_20), 6),
        'ema_distance_50': round(_safe(ema_distance_50), 6),
        'rsi_normalized': round(rsi_norm, 6),
        'macd_histogram_norm': round(_safe(macd_hist_norm), 6),
        'atr_pct': round(_safe(atr_pct), 6),
        'volume_ratio': round(volume_ratio, 6),
        'trend_encoded': trend_encoded,
        'atr_percentile': round(atr_percentile, 4),
        '_degraded': degraded,
    }


def _atr_percentile(candles: list, current_atr) -> float:
    """Percentile rank (0-100) of the current ATR among trailing ATR values.

    Computes the real rolling ATR series, drops the most recent point (the one
    that *is* ``current_atr``), and ranks the current value against the trailing
    200. Ties are credited half, so a flat (constant-ATR) history lands at 50%
    -> 'medium' rather than collapsing to an extreme. 0.0 if insufficient data.
    """
    if current_atr is None or len(candles) < 50:
        return 0.0
    from .indicators import atr as atr_series

    series = atr_series(
        [c.high for c in candles], [c.low for c in candles],
        [c.close for c in candles], 14,
    )
    defined = [x for x in series if x is not None]
    if len(defined) < 20:
        return 0.0
    window = defined[-201:-1]  # trailing history, exclude the self point
    if not window:
        return 0.0
    less = sum(1 for v in window if v < current_atr)
    equal = sum(1 for v in window if abs(v - current_atr) < 1e-12)
    return (less + 0.5 * equal) / len(window) * 100.0