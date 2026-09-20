"""Phase 15 — Deterministic market regime detection.

Classifies the current market into a {trend} × {volatility} label derived purely
from computed indicators and candle ranges. No randomness, no LLM, no lookahead.
"""
from __future__ import annotations

from .features import _atr_percentile


def detect_regime(candles: list, indicators: dict) -> dict:
    """Classify the current regime for a symbol/timeframe.

    Returns
    -------
    {
        trend: 'bullish' | 'bearish' | 'neutral',
        volatility: 'high' | 'medium' | 'low',
        regime_label: 'bullish_trending_high_vol',
        atr_percentile: float,   # 0-100 rank of current ATR vs trailing ranges
        trend_strength: float,   # |ema_distance_50|, how far from the 50 bar.
    }
    """
    trend = indicators.get('trend', 'neutral')
    atr = indicators.get('atr14')
    price = candles[-1].close if candles else None

    percentile = _atr_percentile(candles, atr)
    if not candles or atr is None or not price:
        volatility = 'low'
    elif percentile >= 75.0:
        volatility = 'high'
    elif percentile <= 25.0:
        volatility = 'low'
    else:
        volatility = 'medium'

    # Trend strength: normalized distance from the 50-EMA (0..~5% typical).
    ema50 = indicators.get('ema50')
    trend_strength = abs((price - ema50) / ema50 * 100.0) if (price and ema50) else 0.0

    regime_label = f'{trend}_{volatility}'
    return {
        'trend': trend,
        'volatility': volatility,
        'regime_label': regime_label,
        'atr_percentile': round(percentile, 4),
        'trend_strength': round(trend_strength, 4),
    }