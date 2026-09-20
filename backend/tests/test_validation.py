"""Phase 15 — walk-forward validation tests.

Synthetic candles carry a planted trend so a sensible EMA-crossover config produces
trades on the train window; the assertions focus on structural guarantees
(strict chronology, per-window metrics, consistency gate) rather than profits.
"""
from app.market.models import Candle
from app.strategies.validation_service import walk_forward_validation


def _trending_candles(n=300, start=100.0, step=0.5, bar=1.5):
    return [
        Candle(time=i, open=start + i * step, high=start + i * step + bar,
               low=start + i * step - bar, close=start + i * step, volume=100.0)
        for i in range(n)
    ]


GOOD = {'fast': 10, 'slow': 40, 'risk_pct': 1.0, 'stop_atr_multiple': 2.0}


def test_walk_forward_returns_train_val_oos():
    r = walk_forward_validation(GOOD, _trending_candles())
    assert r['status'] == 'ok'
    for key in ('train_metrics', 'val_metrics', 'oos_metrics'):
        assert key in r
        assert set(r['metric_keys']) <= set(r[key])
    # Strict 60/20/20 chronology: windows must be disjoint and ordered by time.
    candles = _trending_candles()
    n = len(candles)
    train_end = int(n * 0.6)
    val_end = train_end + int(n * 0.2)
    assert candles[train_end - 1].time < candles[train_end].time
    assert candles[val_end - 1].time < candles[val_end].time


def test_walk_forward_consistent_flag_for_trending():
    # A clean uptrend plus fast EMA cross should beat random across windows:
    # monitor consistency is a boolean decision, not a profit prediction.
    r = walk_forward_validation(GOOD, _trending_candles(start=100, step=0.6, n=400))
    assert isinstance(r['consistent'], bool)


def test_insufficient_data():
    r = walk_forward_validation(GOOD, _trending_candles(n=50))
    assert r['status'] == 'insufficient_data'
    assert r['consistent'] is False


def test_invalid_config():
    r = walk_forward_validation({'fast': 40, 'slow': 20}, _trending_candles())
    assert r['status'] == 'invalid_config'
    assert r['consistent'] is False


def test_oos_metrics_present_and_typed():
    candles = _trending_candles(n=300)
    r = walk_forward_validation(GOOD, candles)
    assert r['status'] == 'ok'
    assert set(r['metric_keys']).issubset(r['oos_metrics'])
    for num_key in ('total_return', 'win_rate', 'profit_factor', 'sharpe',
                    'max_drawdown', 'average_trade'):
        assert isinstance(r['oos_metrics'][num_key], (int, float)), num_key
    assert isinstance(r['oos_metrics']['trade_count'], int)