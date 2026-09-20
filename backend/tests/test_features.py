"""Phase 15 — feature engineering tests (deterministic, hand-computed values)."""
import math

from app.engine.features import calculate_features
from app.market.models import Candle


def _candles(n=220, close=100.0, step=0.0, volume=100.0):
    candles = []
    for i in range(n):
        c = close + i * step
        candles.append(Candle(time=i, open=c, high=c + 1, low=c - 1, close=c, volume=volume))
    return candles


def _indicators(trend='bullish', rsi=60.0, atr=2.0, ema20=99.0, ema50=98.0, macd_hist=0.5):
    return {
        'trend': trend, 'rsi14': rsi, 'atr14': atr,
        'ema20': ema20, 'ema50': ema50, 'macd_histogram': macd_hist,
    }


def test_features_flat_and_no_nan_inf():
    feats = calculate_features(_candles(), _indicators())
    limited = {k: v for k, v in feats.items() if k != '_degraded'}
    for f, v in limited.items():
        assert isinstance(v, float), f
        assert math.isfinite(v), f
    assert feats['_degraded'] is False


def test_trend_encoded_matrix():
    for label, enc in [('bullish', 1.0), ('neutral', 0.0), ('bearish', -1.0)]:
        feats = calculate_features(_candles(), _indicators(trend=label))
        assert feats['trend_encoded'] == enc


def test_flat_price_gives_zero_returns():
    feats = calculate_features(_candles(close=100.0, step=0.0), _indicators())
    assert feats['returns_1'] == 0.0
    assert feats['returns_5'] == 0.0
    assert feats['returns_20'] == 0.0


def test_returns_hand_calculated():
    # Rising 1% per candle: last close = 100 + 219 = 319; 20 back = 299.
    feats = calculate_features(_candles(n=220, close=100.0, step=1.0), _indicators())
    close = 319.0
    assert feats['returns_1'] == round((close / (close - 1) - 1) * 100, 6)
    assert feats['returns_20'] == round((close / (close - 20) - 1) * 100, 6)


def test_rsi_normalized():
    feats = calculate_features(_candles(), _indicators(rsi=80.0))
    assert feats['rsi_normalized'] == 0.8
    feats = calculate_features(_candles(), _indicators(rsi=None))
    assert feats['rsi_normalized'] == 0.0


def test_atr_pct_hand_calculated():
    feats = calculate_features(_candles(), _indicators(atr=2.0))
    # odd: atr=2 on price=100 -> (2 / 100) * 100 = 2.0
    assert feats['atr_pct'] == round((2.0 / 100.0) * 100.0, 6)


def test_ema_distance_hand_calculated():
    feats = calculate_features(_candles(close=100.0), _indicators(ema20=95.0, ema50=90.0))
    assert feats['ema_distance_20'] == round((100 - 95) / 95 * 100, 6)
    assert feats['ema_distance_50'] == round((100 - 90) / 90 * 100, 6)


def test_empty_candles_degraded_without_crash():
    feats = calculate_features([], _indicators())
    assert feats['_degraded'] is True


def test_short_history_degraded():
    feats = calculate_features(_candles(n=2), _indicators())
    assert feats['_degraded'] is True


def test_atr_percentile_bounds():
    feats = calculate_features(_candles(), _indicators(atr=2.0))
    assert 0.0 <= feats['atr_percentile'] <= 100.0


def test_volume_ratio_present():
    feats = calculate_features(_candles(volume=100.0), _indicators())
    assert isinstance(feats['volume_ratio'], float)
    assert feats['volume_ratio'] >= 0.0